from enum import Enum
import itertools
import json
import math
import filetype
import os
import re
import sys
from glob import glob
from pathlib import Path
from typing import Dict, List, Optional
from xml.dom import ValidationErr

from natsort import natsorted
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps
from pydantic import BaseModel, model_validator

import page_manager
import size_convert
from enums import Registration, Orientation, OrientationMode, Variant

def configure_console_encoding() -> None:
    """Reconfigure stdout/stderr to UTF-8, so printing non-ASCII card names
    doesn't crash with UnicodeEncodeError on narrow console codepages (e.g.
    Windows cp1252). Call once at CLI startup, not at import time, so this
    module doesn't rewrite an embedding process's stdout/stderr as a side effect."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            try:
                stream.reconfigure(encoding='utf-8', errors='backslashreplace')
            except Exception:
                pass

# Specify directory locations
# Use Path(__file__).parent to ensure paths work regardless of where script is run from
SCRIPT_DIR = Path(__file__).parent
asset_directory = SCRIPT_DIR / 'assets'

layouts_filename = 'layouts.json'
layouts_path = asset_directory / layouts_filename

# Optional extra layout definitions to merge on top of layouts.json. Lets a layout-consuming
# project layer its own card sizes, paper sizes, and layouts on top of this repo's without
# modifying it. Opt-in: both are empty/unset by default, so load_layout_config() behaves
# exactly as if this didn't exist. Two ways to supply extra files, merged in this order:
#   1. Drop any number of *.json files into EXTRA_LAYOUTS_DIR (merged in filename order) -
#      no configuration needed, just copy a file in.
#   2. Point EXTRA_LAYOUTS_ENV at one or more file paths (os.pathsep-separated, merged in
#      order) - for files that live outside EXTRA_LAYOUTS_DIR.
EXTRA_LAYOUTS_DIR = asset_directory / 'extra_layouts'
EXTRA_LAYOUTS_ENV = 'SCM_EXTRA_LAYOUTS'

# Optional override for where cutting templates get written/read (default: SCRIPT_DIR-relative
# cutting_templates/ directories in generate_dxf.py and dxf_to_studio3.py).
CUTTING_TEMPLATES_DIR_ENV = 'SCM_CUTTING_TEMPLATES_DIR'

# Specify valid mimetypes for images
# List can be found here: https://github.com/h2non/filetype.py?tab=readme-ov-file#image
# Pillow suported formats: https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html
valid_mimetypes = (
    # "image/vnd.dwg",
    # "image/x-xcf",
    "image/jpeg",
    "image/jpx",
    # "image/jxl",
    "image/png",
    "image/apng",
    "image/gif",
    "image/webp",
    # "image/x-canon-cr2",
    "image/tiff",
    "image/bmp",
    # "image/vnd.ms-photo",
    # "image/vnd.adobe.photoshop",
    # "image/x-icon",
    # "image/heic",
    "image/avif",
    "image/qoi",
    "image/dds"
)

def guess_extension(data: bytes, default: str = '.png') -> str:
    """Sniff the file extension from raw image bytes, falling back to `default`."""
    kind = filetype.guess(data)
    return f'.{kind.extension}' if kind else default

# Approximately 1.25mm of bleed assuming 300 PPI: ceil(1.25mm * 1in/25.4mm * 300ppi)
MINIMUM_BLEED = 15


class CardSizeDef(BaseModel):
    width: str
    height: str
    radius: Optional[str] = None
    aliases: Optional[List[str]] = None



class RegistrationSettings(BaseModel):
    inset: Optional[str] = None
    thickness: Optional[str] = None
    length: Optional[str] = None


class VariantRegistrationSettings(BaseModel):
    default: RegistrationSettings
    borderless: RegistrationSettings


class DefaultSettings(BaseModel):
    card_radius: str
    registration: VariantRegistrationSettings


class SpecialtyCardSizeDef(BaseModel):
    name: Optional[str] = None
    width: Optional[str] = None
    height: Optional[str] = None
    radius: Optional[str] = None


class SpecialtyPaperSizeDef(BaseModel):
    name: Optional[str] = None
    width: Optional[str] = None
    height: Optional[str] = None


class SpecialtyLayoutDef(BaseModel):
    card_size: SpecialtyCardSizeDef
    paper_size: SpecialtyPaperSizeDef
    orientation: Orientation = Orientation.LANDSCAPE
    registration_orientation: Optional[Orientation] = None
    version: int = 1
    num_rows: Optional[int] = None
    num_cols: Optional[int] = None
    registration: Optional[RegistrationSettings] = None


class FitMode(str, Enum):
    STRETCH = "stretch"
    CROP = "crop"

class ImageFormat(str, Enum):
    """Formats usable with --output_images. Pages always have a transparent
    background, so only alpha-capable formats are offered."""
    PNG = "png"
    WEBP = "webp"
    TIFF = "tiff"

class CardLayoutSize(BaseModel):
    width: int
    height: int

class PaperSizeDef(BaseModel):
    width: str
    height: str
    aliases: Optional[List[str]] = None

    @model_validator(mode='after')
    def width_gte_height(self) -> 'PaperSizeDef':
        w = size_convert.size_to_mm(self.width)
        h = size_convert.size_to_mm(self.height)
        if w < h:
            raise ValueError(f'Paper width ({self.width}) must be >= height ({self.height}). Paper sizes are stored as landscape.')
        return self

class CardLayout(BaseModel):
    orientation: Orientation
    registration_orientation: Optional[Orientation] = None
    version: int
    num_rows: Optional[int] = None
    num_cols: Optional[int] = None
    registration: Optional[RegistrationSettings] = None

class LayoutConfig(BaseModel):
    ppi: int
    defaults: DefaultSettings
    card_sizes: Dict[str, CardSizeDef]
    paper_sizes: Dict[str, PaperSizeDef]
    layouts: Dict[str, Dict[str, Dict[str, CardLayout]]]  # layouts[paper][card][variant]
    specialty_layouts: Optional[Dict[str, SpecialtyLayoutDef]] = None


def extra_layout_paths() -> list[Path]:
    """Return every extra layout file, in merge/precedence order.

    Every *.json file found in EXTRA_LAYOUTS_DIR (sorted by filename), followed by every
    file listed in EXTRA_LAYOUTS_ENV (an os.pathsep-separated list). Empty if neither is
    configured.
    """
    dir_paths = sorted(EXTRA_LAYOUTS_DIR.glob('*.json')) if EXTRA_LAYOUTS_DIR.is_dir() else []
    env_paths = [Path(p) for p in os.environ.get(EXTRA_LAYOUTS_ENV, '').split(os.pathsep) if p]
    return dir_paths + env_paths


def find_extra_layout_owner(section: str, key: str) -> Path | None:
    """Return the first file from extra_layout_paths() whose `section` dict already
    contains `key` (e.g. section='card_sizes', key='mtg'), or None if none do."""
    for path in extra_layout_paths():
        with open(path, 'r') as f:
            if key in json.load(f).get(section, {}):
                return path
    return None


def merge_extra_layouts(raw_config: dict) -> dict:
    """Merge extra card_sizes/paper_sizes/layouts on top of raw_config, in place.

    Merges every file from extra_layout_paths(), in order, into raw_config's
    card_sizes/paper_sizes/layouts dicts. Each key (card size, paper size, or
    paper+card+variant layout) must be new: raise ValueError on any collision with raw_config
    or an earlier file in the merge, since these files are meant to be pure additions, not
    overrides. No-op if extra_layout_paths() is empty.
    """
    for path in extra_layout_paths():
        with open(path, 'r') as f:
            extra = json.load(f)

        for section in ('card_sizes', 'paper_sizes'):
            for key, value in extra.get(section, {}).items():
                if key in raw_config[section]:
                    raise ValueError(f"'{key}' in {section} of {path} already defined")
                raw_config[section][key] = value

        for paper, cards in extra.get('layouts', {}).items():
            for card, variants in cards.items():
                for variant, layout_def in variants.items():
                    if variant in raw_config['layouts'].get(paper, {}).get(card, {}):
                        raise ValueError(f"layout '{paper}'/'{card}'/'{variant}' in {path} already defined")
                    raw_config['layouts'].setdefault(paper, {}).setdefault(card, {})[variant] = layout_def

    return raw_config


def resolve_cutting_templates_dir(default: Path) -> Path:
    """Return the CUTTING_TEMPLATES_DIR_ENV override if set, else default."""
    override = os.environ.get(CUTTING_TEMPLATES_DIR_ENV)
    return Path(override) if override else default


def load_layout_config() -> LayoutConfig:
    """Load and validate layouts.json from the assets directory, merging in any extra
    layout definitions from EXTRA_LAYOUTS_ENV."""
    with open(layouts_path, 'r') as f:
        raw_config = json.load(f)
    merge_extra_layouts(raw_config)
    return LayoutConfig(**raw_config)


# Borderless mode tricks Silhouette Studio into using a smaller effective inset than its
# 10mm minimum (MIN_REG_INSET_MM) by inflating the declared paper size. The software
# still places registration marks at 10mm from the declared edge, but since the declared
# paper is larger than the real sheet, the marks land closer to the actual paper edge.
#
# BORDERLESS_INSET_MM: the effective inset on the real paper (from layouts.json defaults).
# BORDERLESS_EXPANSION_MM: how much to add to each paper dimension in Silhouette Studio
#   so that the 10mm studio inset becomes BORDERLESS_INSET_MM on the real sheet.
#   Formula: each side gains (MIN_REG_INSET_MM - BORDERLESS_INSET_MM), times 2 for both sides.
_layout_config = load_layout_config()
BORDERLESS_INSET_MM = size_convert.size_to_mm(_layout_config.defaults.registration.borderless.inset)
BORDERLESS_EXPANSION_MM = (page_manager.MIN_REG_INSET_MM - BORDERLESS_INSET_MM) * 2


def resolve_card_size_alias(layout_config: LayoutConfig, card_size: str) -> str:
    """Resolve a card size alias to its canonical name. Returns the original if not an alias."""
    for name, card_def in layout_config.card_sizes.items():
        if card_def.aliases and card_size in card_def.aliases:
            print(f'Card size "{card_size}" is an alias of "{name}". Using "{name}" card size and cutting template.')
            return name
    return card_size


def resolve_paper_size_alias(layout_config: LayoutConfig, paper_size: str) -> str:
    """Resolve a paper size alias to its canonical name. Returns the original if not an alias."""
    for name, paper_def in layout_config.paper_sizes.items():
        if paper_def.aliases and paper_size in paper_def.aliases:
            print(f'Paper size "{paper_size}" is an alias of "{name}". Using "{name}" paper size and cutting template.')
            return name
    return paper_size


def get_all_card_size_names(layout_config: LayoutConfig) -> List[str]:
    """Return all valid card size names: canonical names and their aliases.
    standard, poker, bridge first; then alphabetical; then names starting with a digit."""
    names = list(layout_config.card_sizes.keys())
    for card_def in layout_config.card_sizes.values():
        if card_def.aliases:
            names.extend(card_def.aliases)
    priority = ["standard", "poker", "bridge"]
    priority_names = [n for n in priority if n in names]
    rest = sorted((n for n in names if n not in priority), key=lambda n: (n[0].isdigit(), n))
    return priority_names + rest


def get_all_paper_size_names(layout_config: LayoutConfig) -> List[str]:
    """Return all valid paper size names: canonical names and their aliases.
    letter, tabloid, a4, a3, arch_b first; then alphabetical; then names starting with a digit."""
    names = list(layout_config.paper_sizes.keys())
    for paper_def in layout_config.paper_sizes.values():
        if paper_def.aliases:
            names.extend(paper_def.aliases)
    priority = ["letter", "tabloid", "a4", "a3", "arch_b"]
    priority_names = [n for n in priority if n in names]
    rest = sorted((n for n in names if n not in priority), key=lambda n: (n[0].isdigit(), n))
    return priority_names + rest


def get_all_specialty_layout_names(layout_config: LayoutConfig) -> List[str]:
    """Return all specialty layout names, sorted alphabetically."""
    if not layout_config.specialty_layouts:
        return []
    return sorted(layout_config.specialty_layouts.keys())


def template_name(paper_size: str, card_size: str, variant: Variant, version: int) -> str:
    """Compose the standard template name: {paper_size}-{card_size}-{variant}-v{version}.

    Note: 'default' variant is omitted from the name for backwards compatibility.
    Examples:
        - default: letter-bridge-v4
        - borderless: letter-bridge-borderless-v1
    """
    if variant == Variant.DEFAULT:
        return f"{paper_size}-{card_size}-v{version}"
    else:
        return f"{paper_size}-{card_size}-{variant.value}-v{version}"


# Known junk files across OSes
EXTRANEOUS_FILES = {
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
    "Icon\r",  # macOS oddball
}

def parse_crop_string(crop_string: str | None, card_width: int, card_height: int) -> tuple[float, float]:
    """
    Calculates crop based on various formats.

    "9" -> (9, 9)
    "3mm" -> calls function to determine mm crop
    "3in" -> calls function to determine in crop
    """
    if crop_string is None:
        return 0, 0

    crop_string = crop_string.strip().lower()

    float_pattern = r"(?:\d+\.\d*|\.\d+|\d+)"  # matches 1.0, .5, or 2

    # Match "3mm" or "3.5mm"
    mm_match = re.fullmatch(rf"({float_pattern})mm", crop_string)
    if mm_match:
        crop_mm = float(mm_match.group(1))
        return convertInToCrop(crop_mm / 25.4, card_width, card_height)

    # Match "0.1in" or "0.125in"
    in_match = re.fullmatch(rf"({float_pattern})in", crop_string)
    if in_match:
        crop_in = float(in_match.group(1))
        return convertInToCrop(crop_in, card_width, card_height)

    # Match single float like "6.5" or "4.5"
    single_match = re.fullmatch(float_pattern, crop_string)
    if single_match:
        num = float(crop_string)
        return num, num

    raise ValueError(f"Invalid crop format: '{crop_string}'")

def parse_dimension_string(dimension_string: str | None, ppi: int) -> int:
    """
    Parse a dimension string and return the value in pixels.

    Supports the same formats as --crop for consistency:
    - Physical units: "3mm", "0.125in"
    - Pixels: "6.5", "10"
    - Disabled: "0" or None

    Args:
        dimension_string: String like "3mm", "0.125in", "6.5" (pixels), or "0" to disable
        ppi: Pixels per inch for the layout

    Returns:
        Dimension in pixels
    """
    if dimension_string is None or dimension_string == "0":
        return 0

    dimension_string = dimension_string.strip().lower()

    if dimension_string == "0":
        return 0

    float_pattern = r"(?:\d+\.\d*|\.\d+|\d+)"

    # Match "3mm" or "3.5mm"
    mm_match = re.fullmatch(rf"({float_pattern})mm", dimension_string)
    if mm_match:
        value_mm = float(mm_match.group(1))
        return math.floor(value_mm / 25.4 * ppi)

    # Match "0.1in" or "0.125in"
    in_match = re.fullmatch(rf"({float_pattern})in", dimension_string)
    if in_match:
        value_in = float(in_match.group(1))
        return math.floor(value_in * ppi)

    # Match single float like "6.5" or "4.5" (pixels)
    single_match = re.fullmatch(float_pattern, dimension_string)
    if single_match:
        return int(float(dimension_string))

    raise ValueError(f"Invalid dimension format: '{dimension_string}'")


def convertInToCrop(crop_in: float, card_width_px: int, card_height_px: int) -> tuple[float, float]:
    # Convert from pixels to physical mm using DPI
    # Card dimensions are based on 300 ppi
    card_width_mm = card_width_px / 300
    card_height_mm = card_height_px / 300

    crop_x_percent = 2 * crop_in / card_width_mm * 100
    crop_y_percent = 2 * crop_in / card_height_mm * 100

    return (crop_x_percent, crop_y_percent)

def delete_hidden_files_in_directory(path: str):
    if len(path) > 0:
        for file in os.listdir(path):
            full_path = os.path.join(path, file)
            if os.path.isfile(full_path) and (file in EXTRANEOUS_FILES or file.startswith("._")):
                try:
                    os.remove(full_path)
                    print(f"Removed hidden file: {full_path}")
                except OSError as e:
                    print(f"Could not remove {full_path}: {e}")

def get_directory(path):
    if os.path.isdir(path):
        return os.path.abspath(path)
    else:
        return os.path.abspath(os.path.dirname(path))

def ensure_directory(path: str) -> str:
    """Create directory and any missing parent directories. Returns the path."""
    os.makedirs(path, exist_ok=True)
    return path

def ensure_output_directory(output_path: str) -> None:
    """Create the parent directory of output_path if it doesn't exist."""
    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)

def get_image_file_paths(dir_path: str) -> List[str]:
    result = []

    for current_folder, _, files in os.walk(dir_path):
        for filename in files:
            full_path = os.path.join(current_folder, filename)

            # Skip invalid files
            if filetype.guess_mime(full_path) not in valid_mimetypes:
                continue

            relative_path = os.path.relpath(full_path, dir_path)
            result.append(relative_path)

    return result

def get_back_card_image_path(back_dir_path) -> str | None:
    # List all files in the directory that are pngs and jpegs
    # The directory may contain markdown and/or other files
    files = [f for f in Path(back_dir_path).glob("*") if f.is_file() and filetype.guess_mime(f) in valid_mimetypes]

    if len(files) == 0:
        return None

    if len(files) == 1:
        return files[0]

    # Multiple back files detected, provide a selection menu
    print("[0] No back image")
    for i, f in enumerate(files):
        print(f'[{i + 1}] {f}')

    while True:
        choice = input("Select a back image (enter the number): ")

        if not choice.isdigit():
            continue

        index = int(choice) - 1
        if index == -1:
            return None
        if index >= 0 and index < len(files):
            break

    return files[index]

def crop_and_scale_image(
    card_image: Image.Image,
    crop_percent_x: float,
    crop_percent_y: float,
    scaled_width: int,
    scaled_height: int,
    scaled_bleed_width: int,
    scaled_bleed_height: int,
    fit: FitMode = FitMode.STRETCH
) -> tuple[Image.Image, int, int, tuple[int, int]]:
    """
    Crop and scale a card image, returning the processed image and bleed offsets.

    When fit == STRETCH (default), each axis scales independently.
    When fit == CROP, a uniform scale ratio is used (preserving aspect ratio),
    and excess image data on the non-limiting axis is used for real bleed.

    Returns:
        tuple of:
        - processed_image: The cropped and scaled card image
        - bleed_offset_x: X position adjustment when bleed is included in image (negative or 0)
        - bleed_offset_y: Y position adjustment when bleed is included in image (negative or 0)
        - synthetic_bleed: (width, height) of bleed to generate artificially, (0, 0) if real bleed was used
    """
    card_width, card_height = card_image.size

    # Calculate the original size minus the desired crop: "cropped size"
    cropped_width = math.floor(card_width * (1 - (crop_percent_x / 100)))
    cropped_height = math.floor(card_height * (1 - (crop_percent_y / 100)))

    # Calculate the ratio between the cropped size and the scaled size: "scale ratio"
    if fit == FitMode.CROP:
        # Uniform scaling: use the smaller ratio (the tighter-fitting axis) so that
        # the image fills the entire target area. The other axis has excess image
        # data that gets cropped away or used as real bleed.
        uniform_ratio = min(cropped_width / scaled_width, cropped_height / scaled_height)
        cropped_scaled_ratio_x = uniform_ratio
        cropped_scaled_ratio_y = uniform_ratio
    else:
        cropped_scaled_ratio_x = cropped_width / scaled_width
        cropped_scaled_ratio_y = cropped_height / scaled_height

    # Calculate the size of the card after adding bleed: "bleed size"
    scaled_width_with_bleed = scaled_width + 2 * scaled_bleed_width
    scaled_height_with_bleed = scaled_height + 2 * scaled_bleed_height

    # Calculate the size of the card after adding bleed, but before scaling: "unscaled bleed size"
    unscaled_width_with_bleed = math.floor(scaled_width_with_bleed * cropped_scaled_ratio_x)
    unscaled_height_with_bleed = math.floor(scaled_height_with_bleed * cropped_scaled_ratio_y)

    can_bleed_x = unscaled_width_with_bleed <= card_width
    can_bleed_y = unscaled_height_with_bleed <= card_height

    # Check if the unscaled bleed size is smaller than the original card size
    # If so, we can use real bleed from the card's edge pixels
    if can_bleed_x and can_bleed_y:
        crop_x = (card_width - unscaled_width_with_bleed) // 2
        crop_y = (card_height - unscaled_height_with_bleed) // 2
        card_image = card_image.crop((
            crop_x,
            crop_y,
            card_width - crop_x,
            card_height - crop_y,
        ))
        card_image = card_image.resize((scaled_width_with_bleed, scaled_height_with_bleed))

        # Offset position to account for bleed included in image
        return card_image, -scaled_bleed_width, -scaled_bleed_height, (0, 0)

    # Per-axis bleed paths (CROP mode only — uniform ratio guarantees no distortion)
    if fit == FitMode.CROP:
        if can_bleed_x:
            # Real bleed on X, synthetic on Y
            content_height = min(math.floor(scaled_height * cropped_scaled_ratio_y), card_height)
            crop_x = (card_width - unscaled_width_with_bleed) // 2
            crop_y = (card_height - content_height) // 2
            card_image = card_image.crop((crop_x, crop_y, card_width - crop_x, card_height - crop_y))
            card_image = card_image.resize((scaled_width_with_bleed, scaled_height))
            return card_image, -scaled_bleed_width, 0, (0, scaled_bleed_height)

        if can_bleed_y:
            # Synthetic on X, real bleed on Y
            content_width = min(math.floor(scaled_width * cropped_scaled_ratio_x), card_width)
            crop_x = (card_width - content_width) // 2
            crop_y = (card_height - unscaled_height_with_bleed) // 2
            card_image = card_image.crop((crop_x, crop_y, card_width - crop_x, card_height - crop_y))
            card_image = card_image.resize((scaled_width, scaled_height_with_bleed))
            return card_image, 0, -scaled_bleed_height, (scaled_bleed_width, 0)

        # Neither axis has room for real bleed — center-crop to content area
        content_width = min(math.floor(scaled_width * cropped_scaled_ratio_x), card_width)
        content_height = min(math.floor(scaled_height * cropped_scaled_ratio_y), card_height)
        crop_x = (card_width - content_width) // 2
        crop_y = (card_height - content_height) // 2
        card_image = card_image.crop((crop_x, crop_y, card_width - crop_x, card_height - crop_y))
        card_image = card_image.resize((scaled_width, scaled_height))
        return card_image, 0, 0, (scaled_bleed_width, scaled_bleed_height)

    # STRETCH fallback: crop the card to the cropped size, then resize it to the scaled size
    crop_x = card_width * (crop_percent_x / 100) // 2
    crop_y = card_height * (crop_percent_y / 100) // 2
    card_image = card_image.crop((
        crop_x,
        crop_y,
        card_width - crop_x,
        card_height - crop_y,
    ))
    card_image = card_image.resize((scaled_width, scaled_height))

    return card_image, 0, 0, (scaled_bleed_width, scaled_bleed_height)


def fill_rounded_corners(card_image: Image.Image, corner_radius: int) -> Image.Image:
    """
    Fill the rounded corner regions of a card image with bleed.

    Assumes the card has rounded corners with the specified radius.
    Pixels in the "cut zone" (outside the corner radius arc) are filled
    by extending from the nearest pixel on the arc.

    Args:
        card_image: The card image to modify
        corner_radius: The radius of the rounded corners in pixels

    Returns:
        A new image with filled corners
    """
    import math

    # Create a copy so we don't modify the original
    result = card_image.copy()
    width, height = result.size

    # Define the four corners: (corner_point, center_of_arc)
    corners = [
        ((0, 0), (corner_radius, corner_radius)),  # top-left
        ((width, 0), (width - corner_radius, corner_radius)),  # top-right
        ((0, height), (corner_radius, height - corner_radius)),  # bottom-left
        ((width, height), (width - corner_radius, height - corner_radius)),  # bottom-right
    ]

    for (corner_x, corner_y), (arc_cx, arc_cy) in corners:
        # Each rounded corner has a square region of size (corner_radius x corner_radius)
        # that contains both the rounded arc and the "cut zone" beyond it
        square_x_start = 0 if corner_x == 0 else width - corner_radius
        square_y_start = 0 if corner_y == 0 else height - corner_radius
        square_x_end = corner_radius if corner_x == 0 else width
        square_y_end = corner_radius if corner_y == 0 else height

        # Process each pixel in this corner's square
        for local_x in range(square_x_start, square_x_end):
            for local_y in range(square_y_start, square_y_end):
                # Calculate distance from this pixel to the arc's center point
                dist = math.sqrt((local_x - arc_cx) ** 2 + (local_y - arc_cy) ** 2)

                # Pixels beyond the corner_radius are in the "cut zone" - the area that
                # will be removed when the card is die-cut with rounded corners
                if dist > corner_radius:
                    # Use polar coordinates to find the nearest point on the arc:
                    # 1. Calculate the angle from the arc center to this cut-zone pixel
                    angle = math.atan2(local_y - arc_cy, local_x - arc_cx)

                    # 2. Project that angle onto the arc at exactly corner_radius distance
                    # This gives us the nearest "good" pixel on the rounded corner edge
                    src_x = int(arc_cx + corner_radius * math.cos(angle))
                    src_y = int(arc_cy + corner_radius * math.sin(angle))

                    # Clamp to image bounds for safety
                    src_x = max(0, min(width - 1, src_x))
                    src_y = max(0, min(height - 1, src_y))

                    # Copy the arc pixel into the cut zone, extending the card image
                    # radially outward to fill what would otherwise be white corners
                    try:
                        pixel = result.getpixel((src_x, src_y))
                        result.putpixel((local_x, local_y), pixel)
                    except (IndexError, ValueError):
                        pass

    return result


def draw_card_with_bleed(
    card_image: Image.Image,
    base_image: Image.Image,
    x: int,
    y: int,
    print_bleed: tuple[int, int],
    extra_bleed: tuple[int, int, int, int] = (0, 0, 0, 0)
):
    """
    Draw a card with bleed on all edges.

    Args:
        card_image: The card image to draw
        base_image: The base image to draw on
        x, y: Position to place the card
        print_bleed: Tuple of (bleed_width, bleed_height) in pixels
        extra_bleed: Additional bleed for outer edges (top, right, bottom, left) in pixels
    """
    bleed_width, bleed_height = print_bleed
    extra_top, extra_right, extra_bottom, extra_left = extra_bleed

    # Calculate total bleed for each edge
    bleed_top = bleed_height + extra_top
    bleed_bottom = bleed_height + extra_bottom
    bleed_left = bleed_width + extra_left
    bleed_right = bleed_width + extra_right

    width, height = card_image.size
    base_image.paste(card_image, (x, y))

    class Axis(int, Enum):
        X = 0
        Y = 1

    def extend_edge(crop_box: tuple[int, int, int, int], start: tuple[int, int], bleed: int, axis: Axis):
        for bleed_i in range(bleed):
            pos = (
                start[0] + (bleed_i if axis == Axis.X else 0),
                start[1] + (bleed_i if axis == Axis.Y else 0)
            )
            base_image.paste(card_image.crop(crop_box), pos)

    def fill_corner(corner_pixel_x: int, corner_pixel_y: int,
                    corner_x: int, corner_y: int,
                    width: int, height: int):
        """Fill a corner bleed region by tiling a single pixel."""
        pixel = card_image.crop((corner_pixel_x, corner_pixel_y, corner_pixel_x + 1, corner_pixel_y + 1))
        for dx in range(width):
            for dy in range(height):
                base_image.paste(pixel, (corner_x + dx, corner_y + dy))

    # Extend the edges of the cards to create print bleed
    # Top and bottom
    extend_edge((0, 0, width, 1), (x, y - bleed_top), bleed_top, Axis.Y)
    extend_edge((0, height - 1, width, height), (x, y + height), bleed_bottom, Axis.Y)

    # Left and right
    extend_edge((0, 0, 1, height), (x - bleed_left, y), bleed_left, Axis.X)
    extend_edge((width - 1, 0, width, height), (x + width, y), bleed_right, Axis.X)

    # Fill four corners with tiled pixels from card corners
    fill_corner(0, 0, x - bleed_left, y - bleed_top, bleed_left, bleed_top)  # Top-left
    fill_corner(width - 1, 0, x + width, y - bleed_top, bleed_right, bleed_top)  # Top-right
    fill_corner(0, height - 1, x - bleed_left, y + height, bleed_left, bleed_bottom)  # Bottom-left
    fill_corner(width - 1, height - 1, x + width, y + height, bleed_right, bleed_bottom)  # Bottom-right

    return base_image

def draw_card_layout(
    card_images: List[Image.Image | None],
    single_back_image: Image.Image,
    base_image: Image.Image,
    num_rows: int,
    num_cols: int,
    x_pos: List[int],
    y_pos: List[int],
    width: int,
    height: int,
    print_bleed: tuple[int, int],
    crop: tuple[float, float],
    crop_backs: tuple[float, float],
    ppi_ratio: float,
    extend_edges: int,
    extend_edges_backs: int,
    extend_corners_radius: int,
    extend_corners_backs_radius: int,
    extend_bleed: int,
    flip: bool,
    fit: FitMode,
    fit_backs: FitMode,
    orientation: Orientation
):
    num_cards = num_rows * num_cols
    crop_percent_x, crop_percent_y = crop
    crop_backs_percent_x, crop_backs_percent_y = crop_backs

    extend_edges_thickness = math.floor(extend_edges * ppi_ratio)
    extend_edges_backs_thickness = math.floor(extend_edges_backs * ppi_ratio)
    extend_corners_thickness = math.floor(extend_corners_radius * ppi_ratio)
    extend_corners_backs_thickness = math.floor(extend_corners_backs_radius * ppi_ratio)
    extend_bleed_thickness = math.floor(extend_bleed * ppi_ratio)

    # Calculate the size of the card after scaling: "scaled size"
    scaled_width = math.floor(width * ppi_ratio)
    scaled_height = math.floor(height * ppi_ratio)

    scaled_bleed_width = math.ceil(print_bleed[0] * ppi_ratio)
    scaled_bleed_height = math.ceil(print_bleed[1] * ppi_ratio)

    # Fill all the spaces with the card back
    for i, card_image in enumerate(card_images):
        if card_image is None:
            continue

        # Calculate base position from layout
        col = i % num_cards % num_cols
        row = (i % num_cards) // num_cols
        # Long-side flip: landscape flips rows, portrait flips columns
        if flip:
            if orientation == Orientation.PORTRAIT:
                col = num_cols - col - 1
            else:
                row = num_rows - row - 1

        base_x = math.floor(x_pos[col] * ppi_ratio)
        base_y = math.floor(y_pos[row] * ppi_ratio)

        # Default: use synthetic bleed, no position offset needed
        bleed_offset_x = 0
        bleed_offset_y = 0
        synthetic_bleed = (scaled_bleed_width, scaled_bleed_height)

        # Select parameters based on card type (front vs back).
        # Renaming to active_* allows us to use a single processing path below
        # instead of duplicating the entire image processing logic for fronts and backs.
        if card_image is single_back_image:
            active_crop_x, active_crop_y = crop_backs_percent_x, crop_backs_percent_y
            active_fit = fit_backs
            active_extend_edges_thickness = extend_edges_backs_thickness
            active_extend_corners_thickness = extend_corners_backs_thickness
        else:
            active_crop_x, active_crop_y = crop_percent_x, crop_percent_y
            active_fit = fit
            active_extend_edges_thickness = extend_edges_thickness
            active_extend_corners_thickness = extend_corners_thickness

        # Apply cropping, scaling, and fit mode
        if active_crop_x > 0 or active_crop_y > 0 or active_fit == FitMode.CROP:
            card_image, bleed_offset_x, bleed_offset_y, synthetic_bleed = crop_and_scale_image(
                card_image,
                active_crop_x,
                active_crop_y,
                scaled_width,
                scaled_height,
                scaled_bleed_width,
                scaled_bleed_height,
                active_fit
            )
        else:
            # No percentage crop and STRETCH mode: just scale to target size
            card_image = card_image.resize((scaled_width, scaled_height))

        # Apply extend_edges: simple crop that affects all edges uniformly
        if active_extend_edges_thickness > 0:
            card_image = card_image.crop((
                active_extend_edges_thickness,
                active_extend_edges_thickness,
                card_image.width - active_extend_edges_thickness,
                card_image.height - active_extend_edges_thickness
            ))

        # If extend_corners is specified, fill the corner regions FIRST
        # This modifies the card image so the bleed will be generated from the filled corners
        if active_extend_corners_thickness > 0:
            card_image = fill_rounded_corners(card_image, active_extend_corners_thickness)

        if flip and orientation == Orientation.LANDSCAPE:
            card_image = card_image.rotate(180)

        # Calculate final position
        x = base_x + bleed_offset_x + active_extend_edges_thickness
        y = base_y + bleed_offset_y + active_extend_edges_thickness

        # Calculate total bleed including synthetic bleed and edge extension
        edge_bleed_width = synthetic_bleed[0] + active_extend_edges_thickness
        edge_bleed_height = synthetic_bleed[1] + active_extend_edges_thickness

        # Determine if this card is on an outer edge and should have extended bleed
        # extra_bleed format: (top, right, bottom, left)
        extra_bleed_top = extend_bleed_thickness if row == 0 else 0
        extra_bleed_bottom = extend_bleed_thickness if row == num_rows - 1 else 0
        extra_bleed_left = extend_bleed_thickness if col == 0 else 0
        extra_bleed_right = extend_bleed_thickness if col == num_cols - 1 else 0

        # Generate edge bleed (from the modified card if corners were filled)
        draw_card_with_bleed(
            card_image,
            base_image,
            x,
            y,
            (edge_bleed_width, edge_bleed_height),
            (extra_bleed_top, extra_bleed_right, extra_bleed_bottom, extra_bleed_left)
        )

def draw_outline(
    page: Image.Image,
    x_pos: List[int],
    y_pos: List[int],
    card_width_px: int,
    card_height_px: int,
    radius_px: int,
    ppi_ratio: float,
):
    draw = ImageDraw.Draw(page)
    scaled_w = math.floor(card_width_px * ppi_ratio)
    scaled_h = math.floor(card_height_px * ppi_ratio)
    scaled_r = math.floor(radius_px * ppi_ratio)

    for x in x_pos:
        for y in y_pos:
            sx = math.floor(x * ppi_ratio)
            sy = math.floor(y * ppi_ratio)
            draw.rounded_rectangle(
                [sx, sy, sx + scaled_w, sy + scaled_h],
                radius=scaled_r,
                outline='white',
                width=1,
            )

def add_front_back_pages(front_page: Image.Image, back_page: Image.Image, pages: List[Image.Image], page_width: int, page_height: int, ppi_ratio: float, template: str, only_fronts: bool, label: str, orientation: Orientation, label_margin_px: int, borderless: bool):
    font = ImageFont.truetype(os.path.join(asset_directory, 'arial.ttf'), 40 * ppi_ratio)

    num_sheet = len(pages) + 1
    if not only_fronts:
        num_sheet = int(len(pages) / 2) + 1

    label_text = f'sheet: {num_sheet}, template: {template}'
    if label is not None:
        label_text = f'label: {label}, {label_text}'

    # Label goes on the short side of the paper, opposite the top-left black square.
    # Landscape: short sides are left/right; black square top-left → label on RIGHT.
    # Portrait: short sides are top/bottom; black square top-left → label on BOTTOM.
    if orientation == Orientation.LANDSCAPE:
        # Right side: rotate page, draw horizontal text, rotate back
        front_page = front_page.rotate(-90, expand=True)
        draw = ImageDraw.Draw(front_page)
        label_x = math.floor((page_height / 2) * ppi_ratio)
        label_y = math.floor(page_width * ppi_ratio) - label_margin_px
        draw.text((label_x, label_y), label_text, fill=(0, 0, 0), anchor="mm", font=font)
        front_page = front_page.rotate(90, expand=True)
    else:
        # Bottom side: horizontal text
        draw = ImageDraw.Draw(front_page)
        label_x = math.floor((page_width / 2) * ppi_ratio)
        label_y = math.floor(page_height * ppi_ratio) - label_margin_px
        draw.text((label_x, label_y), label_text, fill=(0, 0, 0), anchor="mm", font=font)

    # Rotate portrait pages to landscape so the generated PDF is always landscape.
    # This ensures offset_pdf.py works regardless of card orientation detection.
    if orientation == Orientation.PORTRAIT:
        front_page = front_page.rotate(90, expand=True)
        back_page = back_page.rotate(90, expand=True)

    # Add a back page for every front page template
    pages.append(front_page)
    if not only_fronts:
        pages.append(back_page)

def check_paths_subset(subset: set[str], mainset: set[str]) -> set[str]:
    """Return the items in `subset` whose basenames do NOT appear in `mainset`,
    ignoring extensions."""
    subset_stems = {Path(p).stem: p for p in subset}
    mainset_stems = {Path(p).stem for p in mainset}

    return {orig for stem, orig in subset_stems.items() if stem not in mainset_stems}

def resolve_image_with_any_extension(path: str) -> str:
    """
    If the exact path exists, return it.
    Otherwise search for files with the same stem (basename)
    but any extension. Returns the resolved path or raises.
    """
    p = Path(path)

    # Case 1: exact file exists
    if p.exists():
        return str(p)

    # Case 2: try to find any file with the same stem
    pattern = str(p.with_suffix('')) + ".*"   # e.g. "card1.*"
    matches = glob(pattern)

    if len(matches) == 0:
        raise FileNotFoundError(f"Missing image: {pattern}")

    if len(matches) > 1:
        raise ValueError(f"Ambiguous image match: {matches}")

    return matches[0]


def find_best_orientation(
    orientation_mode: OrientationMode,
    card_width: str,
    card_height: str,
    paper_width: str,
    paper_height: str,
    inset: str,
    length: str,
    ppi: int,
    preferred: Orientation = Orientation.LANDSCAPE,
) -> tuple[Orientation, page_manager.CardLayout]:
    """Resolve an OrientationMode to a concrete Orientation and compute the layout.

    OrientationMode represents user intent:
      - LANDSCAPE or PORTRAIT: Force a specific orientation (manual control)
      - OPTIMIZE: Try both orientations and automatically pick whichever fits more cards

    Orientation is the concrete result (LANDSCAPE or PORTRAIT).

    Args:
        orientation_mode: User's orientation preference (manual or optimize).
        card_width, card_height: Card dimensions as unit strings (e.g., "2.5in").
        paper_width, paper_height: Paper dimensions as unit strings.
        inset, length: Registration mark parameters as unit strings.
        ppi: Pixels per inch for layout computation.
        preferred: Tiebreaker orientation when OPTIMIZE finds equal card counts.

    Returns:
        (chosen_orientation, computed_layout)

    Raises:
        ValueError if no valid layout exists in any tried card orientation.
    """
    kwargs = dict(
        card_width=card_width,
        card_height=card_height,
        paper_width=paper_width,
        paper_height=paper_height,
        inset=inset,
        length=length,
        ppi=ppi,
    )

    # Manual mode: user specified exact card orientation (LANDSCAPE or PORTRAIT)
    if orientation_mode != OrientationMode.OPTIMIZE:
        orientation = Orientation(orientation_mode.value)
        return orientation, page_manager.generate_layout(orientation=orientation, **kwargs)

    # Optimize mode: try both card orientations and pick the one that fits more cards
    best_count = 0
    best_orientation = preferred
    best_computed = None

    for orient in Orientation:
        try:
            computed = page_manager.generate_layout(orientation=orient, **kwargs)
        except ValueError:
            # This card orientation doesn't produce a valid layout, skip it
            continue
        # Count total cards: rows × columns
        count = len(computed.x_pos) * len(computed.y_pos)
        # Keep this card orientation if it fits more cards, or if it's a tie and matches preferred
        if count > best_count or (count == best_count and orient == preferred):
            best_count = count
            best_orientation = orient
            best_computed = computed

    if best_computed is None:
        raise ValueError("No valid layout in either card orientation.")

    return best_orientation, best_computed


def generate_pdf(
    front_dir_path: str,
    back_dir_path: str,
    ds_dir_path: str,
    output_path: str,
    output_image_format: str | None,
    card_size: str,
    paper_size: str,
    registration: Registration,
    only_fronts: bool,
    fit: FitMode,
    fit_backs: str | None,
    crop_string: str | None,
    crop_backs_string: str | None,
    extend_edges: str | None,
    extend_edges_backs: str | None,
    extend_corners: str | None,
    extend_corners_backs: str | None,
    extend_bleed: str | None,
    extend_bleed_backs: str | None,
    ppi: int,
    quality: int,
    skip_indices: List[int],
    load_offset: bool,
    label: str,
    show_outline: bool = False,
    specialty: Optional[str] = None,
    borderless: bool = False,
    registration_orientation_override: Optional[str] = None,
):
    # Sanity checks for the different directories
    f_path = Path(front_dir_path)
    if not f_path.exists() or not f_path.is_dir():
        raise Exception(f'Front image directory path "{f_path}" is invalid.')

    b_path = Path(back_dir_path)
    if not b_path.exists() or not b_path.is_dir():
        raise Exception(f'Back image directory path "{b_path}" is invalid.')

    ds_path = Path(ds_dir_path)
    if not ds_path.exists() or not ds_path.is_dir():
        raise Exception(f'Double-sided image directory path "{ds_path}" is invalid.')

    # Delete hidden files that may affect image fetching
    delete_hidden_files_in_directory(front_dir_path)
    delete_hidden_files_in_directory(back_dir_path)
    delete_hidden_files_in_directory(ds_dir_path)

    # Sanity check for output images
    output_images = output_image_format is not None
    if output_images:
        try:
            output_image_format = ImageFormat(output_image_format.lower())
        except ValueError:
            raise Exception(f'Unsupported image format "{output_image_format}". Use "png", "webp", or "tiff".')
        output_path = get_directory(output_path)
    else:
        if not output_path.lower().endswith(".pdf"):
            raise Exception(f'Cannot save PDF to output path "{output_path}" because it is not a valid PDF file path.')
        ensure_output_directory(output_path)

    # Get the back image, if it exists
    back_card_image_path = None
    use_default_back_page = True
    if not only_fronts:
        back_card_image_path = get_back_card_image_path(back_dir_path)
        use_default_back_page = back_card_image_path is None
        if use_default_back_page:
            print(f'No back image provided in back image directory \"{back_dir_path}\".')

    front_image_filenames = get_image_file_paths(front_dir_path)
    ds_image_filenames = get_image_file_paths(ds_dir_path)

    # Check if double-sided back images has matching front images
    front_set = set(front_image_filenames)
    ds_set = set(ds_image_filenames)
    diff = check_paths_subset(ds_set, front_set)
    if len(diff) > 0:
        raise Exception(f'Double-sided backs "{ds_set - front_set}" do not have matching fronts. Add the missing fronts to front image directory "{front_dir_path}".')

    if only_fronts:
        if len(ds_set) > 0:
            raise Exception(f'Cannot use "--only_fronts" with double-sided cards. Remove cards from double-side image directory "{ds_dir_path}".')

    layout_config = load_layout_config()
    default_reg = layout_config.defaults.registration.default
    registration_orientation_override = (
        Orientation(registration_orientation_override)
        if registration_orientation_override is not None
        else None
    )

    if borderless and specialty:
        raise Exception('Cannot use --borderless with --specialty. Specialty layouts define their own geometry.')

    if specialty:
        if not layout_config.specialty_layouts or specialty not in layout_config.specialty_layouts:
            raise Exception(f'Specialty layout "{specialty}" not found.')
        spec = layout_config.specialty_layouts[specialty]

        # Resolve card size
        if spec.card_size.name:
            if spec.card_size.name not in layout_config.card_sizes:
                raise Exception(f'Card size "{spec.card_size.name}" not found in card_sizes.')
            base = layout_config.card_sizes[spec.card_size.name]
            card_size_def = CardSizeDef(
                width=base.width,
                height=base.height,
                radius=spec.card_size.radius or base.radius,
            )
        else:
            card_size_def = CardSizeDef(
                width=spec.card_size.width,
                height=spec.card_size.height,
                radius=spec.card_size.radius,
            )

        # Resolve paper size
        if spec.paper_size.name:
            if spec.paper_size.name not in layout_config.paper_sizes:
                raise Exception(f'Paper size "{spec.paper_size.name}" not found in paper_sizes.')
            paper_size_def = layout_config.paper_sizes[spec.paper_size.name]
        else:
            paper_size_def = PaperSizeDef(
                width=spec.paper_size.width,
                height=spec.paper_size.height,
            )

        orientation = spec.orientation
        registration_orientation = spec.registration_orientation or orientation
        if registration_orientation_override is not None:
            registration_orientation = registration_orientation_override
        template = f"{specialty}-v{spec.version}"

        lr = spec.registration or RegistrationSettings()
        effective_inset = lr.inset or default_reg.inset

    else:
        # Resolve aliases
        card_size = resolve_card_size_alias(layout_config, card_size)
        paper_size = resolve_paper_size_alias(layout_config, paper_size)

        # Validate card size
        if card_size not in layout_config.card_sizes:
            raise Exception(f'Unsupported card size "{card_size}". Try card sizes: {list(layout_config.card_sizes.keys())}.')
        card_size_def = layout_config.card_sizes[card_size]

        # Validate paper size
        if paper_size not in layout_config.paper_sizes:
            raise Exception(f'Unsupported paper size "{paper_size}". Try paper sizes: {list(layout_config.paper_sizes.keys())}.')
        paper_size_def = layout_config.paper_sizes[paper_size]

        # Select variant based on borderless flag
        variant = Variant.BORDERLESS if borderless else Variant.DEFAULT

        # Look up layout from nested structure: layouts[paper][card][variant]
        if paper_size not in layout_config.layouts or card_size not in layout_config.layouts[paper_size]:
            raise Exception(f'No layout defined for paper "{paper_size}" with card "{card_size}". Add it to layouts.json.')

        card_layouts = layout_config.layouts[paper_size][card_size]
        if variant.value not in card_layouts:
            raise Exception(f'No {variant.value} layout defined for paper "{paper_size}" with card "{card_size}". Add it to layouts.json.')

        layout_def = card_layouts[variant.value]
        orientation = layout_def.orientation
        registration_orientation = layout_def.registration_orientation or orientation
        if registration_orientation_override is not None:
            registration_orientation = registration_orientation_override
        version = layout_def.version

        # Effective registration: merge per-layout overrides on top of variant defaults
        layout_reg = layout_def.registration
        lr = layout_reg or RegistrationSettings()

        if borderless:
            effective_inset = lr.inset or layout_config.defaults.registration.borderless.inset
        else:
            effective_inset = lr.inset or layout_config.defaults.registration.default.inset

        template = template_name(paper_size, card_size, variant, version)

    effective_thickness = lr.thickness or default_reg.thickness
    effective_length = lr.length or default_reg.length

    # Corner exclusion zone = configured mark length + padding constant
    total_exclusion_mm = size_convert.size_to_mm(default_reg.length) + page_manager.REG_PADDING_MM
    computed = page_manager.generate_layout(
        orientation=orientation,
        card_width=card_size_def.width,
        card_height=card_size_def.height,
        paper_width=paper_size_def.width,
        paper_height=paper_size_def.height,
        inset=effective_inset,
        length=f"{total_exclusion_mm}mm",
        ppi=layout_config.ppi,
    )

    card_width_px = computed.card_width_px
    card_height_px = computed.card_height_px
    page_width_px = computed.paper_width_px
    page_height_px = computed.paper_height_px
    x_pos = computed.x_pos
    y_pos = computed.y_pos

    # Determine the amount of x and y crop
    crop = parse_crop_string(crop_string, card_width_px, card_height_px)
    crop_backs = parse_crop_string(crop_backs_string, card_width_px, card_height_px)

    # Parse extend_edges, extend_corners, and extend_bleed parameters
    extend_edges_px = parse_dimension_string(extend_edges, layout_config.ppi)
    extend_edges_backs_px = parse_dimension_string(extend_edges_backs, layout_config.ppi)
    extend_corners_px = parse_dimension_string(extend_corners, layout_config.ppi)
    extend_corners_backs_px = parse_dimension_string(extend_corners_backs, layout_config.ppi)
    extend_bleed_px = parse_dimension_string(extend_bleed, layout_config.ppi)
    extend_bleed_backs_px = parse_dimension_string(extend_bleed_backs, layout_config.ppi)

    # Parse fit_backs parameter - if not specified, use the same fit mode as fronts
    fit_backs_mode = FitMode(fit_backs) if fit_backs is not None else fit

    # Convert corner radius to pixels for outline drawing
    effective_card_radius = card_size_def.radius or layout_config.defaults.card_radius
    radius_px = size_convert.size_to_pixel(effective_card_radius, layout_config.ppi)

    num_rows = len(y_pos)
    num_cols = len(x_pos)
    num_cards = num_rows * num_cols

    if num_cards == 0:
        raise Exception(f'Card size "{card_size}" does not fit on paper size "{paper_size}".')

    # Check skip indices
    # You can only skip valid indices (within the max card count per page)
    clean_skip_indices = [n for n in skip_indices if n < num_cards]
    ignore_skip_indices = [n for n in skip_indices if n >= num_cards]

    if len(ignore_skip_indices) > 0:
        print(f'Ignoring skip indices that are outside range 0-{num_cards - 1}: {ignore_skip_indices}')

    # If all possible cards are skipped, this may result in an infinite loop
    if len(clean_skip_indices) == num_cards:
        raise Exception(f'You cannot skip all cards per page')

    # The baseline PPI is 300
    ppi_ratio = ppi / 300

    inset_px = size_convert.size_to_pixel(effective_inset, layout_config.ppi)
    thickness_px = size_convert.size_to_pixel(effective_thickness, layout_config.ppi)
    if borderless:
        # Different margin for borderless because of space constraints
        label_margin_px = math.floor(inset_px * ppi_ratio)
    else:
        label_margin_px = math.floor((inset_px - thickness_px * 2) * ppi_ratio)

    # Paper sizes are stored as landscape; portrait registration marks need swapped dimensions.
    # When the registration orientation differs from the card layout, rotate the canvas back
    # to match the layout so cards are placed correctly.
    reg_is_portrait = registration_orientation == Orientation.PORTRAIT
    reg_width  = paper_size_def.height if reg_is_portrait else paper_size_def.width
    reg_height = paper_size_def.width  if reg_is_portrait else paper_size_def.height

    # Load an image with the registration marks
    with page_manager.generate_reg_mark(
        reg_width,
        reg_height,
        effective_inset,
        effective_thickness,
        effective_length,
        layout_config.ppi,
        registration,
    ) as reg_im:
        reg_im = reg_im.resize([math.floor(reg_im.width * ppi_ratio), math.floor(reg_im.height * ppi_ratio)])

        if registration_orientation != orientation:
            reg_im = reg_im.rotate(90 if reg_is_portrait else -90, expand=True)

        # Create the array that will store the filled templates
        pages: List[Image.Image] = []

        max_print_bleed = calculate_max_print_bleed(x_pos, y_pos, card_width_px, card_height_px, MINIMUM_BLEED)

        # Load and cache the single back image for reuse
        # Do this if we expect both front and back pages and if we have a back image
        # use_default_back_page indicates no back image was found
        single_back_image = None
        if not only_fronts and not use_default_back_page:
            try:
                # We know the exact image path so we do not need resolve_image_with_any_extension()
                single_back_image = Image.open(back_card_image_path)
                single_back_image = ImageOps.exif_transpose(single_back_image)
            except FileNotFoundError:
                print(f'Cannot get back image "{back_card_image_path}".')
                single_back_image = None
            except OSError as e:
                raise OSError(f'Failed to load back image "{back_card_image_path}": {e}') from e

        # Create card layout
        num_image = 1
        # First iterate on single-sided cards, then iterate on double-sided cards
        it = iter(natsorted(list(check_paths_subset(front_set, ds_set))) + natsorted(list(ds_set)))
        while True:
            file_group = list(itertools.islice(it, num_cards - len(clean_skip_indices)))
            if not file_group:
                break

            # Fetch card art in batches
            # Batch size is based on cards per page
            front_card_images = []
            back_card_images = []
            file_group_iterator = iter(file_group)
            for i in range(num_cards):
                if i in clean_skip_indices:
                    front_card_images.append(None)
                    back_card_images.append(None)
                    continue

                try:
                    file = next(file_group_iterator)
                except StopIteration:
                    break

                print(f'Image {num_image}: {file}')
                num_image += 1

                front_card_image_path = os.path.join(front_dir_path, file)
                # Allow differing extensions for double-sided images
                # Iteration is a combination of front and double-sided image paths
                front_card_image_path = resolve_image_with_any_extension(front_card_image_path)
                try:
                    front_card_image = Image.open(front_card_image_path)
                    front_card_image = ImageOps.exif_transpose(front_card_image)
                except OSError as e:
                    raise OSError(f'Failed to load front image "{front_card_image_path}": {e}') from e
                front_card_images.append(front_card_image)

                if only_fronts:
                    back_card_images.append(None)
                    continue

                # Add double-sided back image
                if file in ds_set:
                    ds_card_image_path = os.path.join(ds_dir_path, file)
                    # Allow differing extensions for double-sided images
                    # Iteration is a combination of front and double-sided image paths
                    ds_card_image_path = resolve_image_with_any_extension(ds_card_image_path)
                    try:
                        ds_card_image = Image.open(ds_card_image_path)
                        ds_card_image = ImageOps.exif_transpose(ds_card_image)
                    except OSError as e:
                        raise OSError(f'Failed to load double-sided image "{ds_card_image_path}": {e}') from e
                    back_card_images.append(ds_card_image)
                    continue

                back_card_images.append(single_back_image)

            front_page = reg_im.copy()
            back_page = reg_im.copy()

            # Create front layout
            draw_card_layout(
                front_card_images,
                single_back_image,
                front_page,
                num_rows,
                num_cols,
                x_pos,
                y_pos,
                card_width_px,
                card_height_px,
                max_print_bleed,
                crop,
                crop_backs,
                ppi_ratio,
                extend_edges_px,
                extend_edges_backs_px,
                extend_corners_px,
                extend_corners_backs_px,
                extend_bleed_px,
                flip=False,
                fit=fit,
                fit_backs=fit_backs_mode,
                orientation=orientation,
            )

            # Create back layout
            draw_card_layout(
                back_card_images,
                single_back_image,
                back_page,
                num_rows,
                num_cols,
                x_pos,
                y_pos,
                card_width_px,
                card_height_px,
                max_print_bleed,
                crop,
                crop_backs,
                ppi_ratio,
                extend_edges_px,
                extend_edges_backs_px,
                extend_corners_px,
                extend_corners_backs_px,
                extend_bleed_backs_px,
                flip=True, # Flip the back sides
                fit=fit,
                fit_backs=fit_backs_mode,
                orientation=orientation,
            )

            # Draw cutting path outlines on top of the card images
            if show_outline:
                draw_outline(front_page, x_pos, y_pos, card_width_px, card_height_px, radius_px, ppi_ratio)
                draw_outline(back_page, x_pos, y_pos, card_width_px, card_height_px, radius_px, ppi_ratio)

            # Add the front and back layouts (also handles portrait→landscape rotation)
            add_front_back_pages(
                front_page,
                back_page,
                pages,
                page_width_px,
                page_height_px,
                ppi_ratio,
                template,
                only_fronts,
                label,
                orientation,
                label_margin_px,
                borderless
            )

        if len(pages) == 0:
            print('No pages were generated')
            return

        # Load saved offset if available
        if load_offset:
            saved_offset = load_saved_offset()

            if saved_offset is None:
                print('Offset cannot be applied')
            else:
                print(f'Loaded x offset: {saved_offset.x_offset}, y offset: {saved_offset.y_offset}, angle offset: {saved_offset.angle_offset}')
                pages = offset_images(pages, saved_offset.x_offset, saved_offset.y_offset, ppi, saved_offset.angle_offset)

        # Save the pages array as a PDF
        if output_images:
            for index, page in enumerate(pages):
                page.save(os.path.join(output_path, f'page{index + 1}.{output_image_format.value}'), format=output_image_format.value.upper(), resolution=math.floor(300 * ppi_ratio), speed=0, subsampling=0, quality=quality)

            print(f'Generated images: {output_path}')

        else:
            pages[0].save(output_path, format='PDF', save_all=True, append_images=pages[1:], resolution=math.floor(300 * ppi_ratio), speed=0, subsampling=0, quality=quality)
            print(f'Generated PDF: {output_path}')


class OffsetData(BaseModel):
    x_offset: int
    y_offset: int
    angle_offset: float = 0.0

def save_offset(x_offset: int, y_offset: int, angle_offset: float = 0.0) -> None:
    # Create the directory if it doesn't exist
    os.makedirs('data', exist_ok=True)

    # Save the offset data to a JSON file
    with open('data/offset_data.json', 'w') as offset_file:
        offset_file.write(OffsetData(x_offset=x_offset, y_offset=y_offset, angle_offset=angle_offset).model_dump_json(indent=4))

    print('Offset data saved!')

def load_saved_offset() -> OffsetData:
    if os.path.exists('data/offset_data.json'):
        with open('data/offset_data.json', 'r') as offset_file:
            try:
                data = json.load(offset_file)
                return OffsetData(**data)

            except json.JSONDecodeError as e:
                print(f'Cannot decode offset JSON: {e}')

            except ValidationErr as e:
                print(f'Cannot validate offset data: {e}.')

    return None

def offset_images(images: List[Image.Image], x_offset: int, y_offset: int, ppi: int, angle_offset: float = 0.0) -> List[Image.Image]:
    result_images = []

    add_offset = False
    for image in images:
        if add_offset:
            # The back page is rotated 180° in the PDF (long-side flip).
            # In orientation-relative terms: +X = right, -X = left, +Y = up, -Y = down.
            # Negating x_offset compensates for the 180° x-axis flip.
            result = ImageChops.offset(image, math.floor(-x_offset * ppi / 300), math.floor(y_offset * ppi / 300))
            # Apply angle rotation if specified
            # Negative angle because PIL rotates counter-clockwise, but we want positive = clockwise
            if angle_offset != 0.0:
                fillcolor = (0, 0, 0, 0) if image.mode == 'RGBA' else 'white'
                result = result.rotate(-angle_offset, center=(image.width / 2, image.height / 2), fillcolor=fillcolor)
            result_images.append(result)
        else:
            result_images.append(image)

        add_offset = not add_offset

    return result_images

def calculate_max_print_bleed(x_pos: List[int], y_pos: List[int], width: int, height: int, min_bleed: int = 0) -> tuple[int, int]:
    if len(x_pos) == 1 and len(y_pos) == 1:
        return (min_bleed, min_bleed)

    x_border_max = min_bleed
    if len(x_pos) >= 2:
        x_pos.sort()

        x_pos_0 = x_pos[0]
        x_pos_1 = x_pos[1]

        x_border_max = max(0, math.ceil((x_pos_1 - x_pos_0 - width) / 2))

    y_border_max = min_bleed
    if len(y_pos) >= 2:
        y_pos.sort()

        y_pos_0 = y_pos[0]
        y_pos_1 = y_pos[1]

        y_border_max = max(0, math.ceil((y_pos_1 - y_pos_0 - height) / 2))

    return (x_border_max, y_border_max)
