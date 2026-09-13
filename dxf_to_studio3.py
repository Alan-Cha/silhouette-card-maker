#!/usr/bin/env python3
"""
DXF to Studio3 Converter with Full Automation

**Windows Only** - This script uses GUI automation to control Silhouette Studio
on Windows. It will not work on macOS or Linux.

This script automates Silhouette Studio with mouse interactions for:
- Cutting mat selection (12x12 or 12x24)
- Custom paper size entry
- Page orientation (portrait/landscape)
- Centering cutting paths
- Registration mark settings

Usage:
    python dxf_to_studio3.py single input.dxf output.studio3 --unit mm --paper_size letter
    python dxf_to_studio3.py batch --unit mm
    python dxf_to_studio3.py calibrate

Window Size Strategy:
    The script forces Silhouette Studio to a fixed window size (1920x1080)
    to ensure consistent UI element positions. If your screen is smaller,
    adjust WINDOW_WIDTH and WINDOW_HEIGHT.
"""

import os
import re
import sys
import time
import subprocess
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from enum import Enum
import platform

import click

from enums import Orientation, Variant, Unit
from utilities import load_layout_config, get_all_paper_size_names, resolve_paper_size_alias, LayoutConfig, resolve_cutting_templates_dir, BORDERLESS_EXPANSION_MM
import size_convert
import page_manager

# Platform check - this script only works on Windows
if platform.system() != "Windows":
    print(f"Error: dxf_to_studio3.py only works on Windows (current platform: {platform.system()})", file=sys.stderr)
    print("", file=sys.stderr)
    print("This script uses GUI automation to control Silhouette Studio, which requires Windows.", file=sys.stderr)
    print("To convert DXF files to .studio3 format on macOS/Linux, you must:", file=sys.stderr)
    print("  1. Manually open the DXF file in Silhouette Studio", file=sys.stderr)
    print("  2. Follow the steps in hugo/content/miscellaneous/template.md", file=sys.stderr)
    sys.exit(1)

# pyautogui: Used for mouse/keyboard automation (clicking UI elements, typing, hotkeys).
# FAILSAFE=True enables abort-by-moving-mouse-to-corner safety feature.
import pyautogui
pyautogui.FAILSAFE = True

# pywinauto: Used for window management (connecting to app, resizing, positioning).
# The win32 backend is used throughout for move_window() and rectangle() methods.
from pywinauto import Application


# =============================================================================
# Configuration
# =============================================================================

DEFAULT_STUDIO_PATH = r"C:\Program Files\Silhouette America\Silhouette Studio\Silhouette Studio.exe"

# Fixed window size for consistent coordinates
WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080
WINDOW_X = 0
WINDOW_Y = 0

# Timing (seconds). These defaults work for most machines.
# Use --action_delay on the CLI to increase if Silhouette Studio is slow.
SETTLE_DELAY = 0.2      # Short delay for UI to settle (after select-all, paste, etc.)
ACTION_DELAY = 1.0      # Delay between UI actions (clicking, typing, panel switches)
LONG_DELAY = 5.0        # Long operations (file load, save, startup uses 2x)

# Calibration file location
ASSETS_DIR = Path(__file__).parent / "assets"
CALIBRATION_FILE = ASSETS_DIR / "gui_coordinates.json"

# Batch conversion defaults
TEMPLATES_DIR = resolve_cutting_templates_dir(Path(__file__).parent / "cutting_templates")



class CuttingMat(Enum):
    MAT_12X12 = "12x12"
    MAT_12X24 = "12x24"


@dataclass
class RegistrationSettings:
    """Settings for registration marks.

    All numeric values are in the user-specified unit (mm or in).
    Values are passed directly to Silhouette Studio in that unit.

    Values are clamped by Silhouette Studio to its allowed range,
    so 0 gives the minimum and any very large value gives the maximum.
    """
    enabled: bool = True
    length: float = 0  # 0 will default to minimum allowed by Silhouette Studio
    thickness: float = 0  # 0 will default to minimum allowed by Silhouette Studio
    inset: float = 0  # 0 will default to minimum allowed by Silhouette Studio


def determine_cutting_mat(width_in: float, height_in: float) -> CuttingMat:
    """Determine which cutting mat fits the page size.

    12x12 mat: both dimensions <= 12 inches.
    12x24 mat: one dimension <= 12 inches, other <= 24 inches.
    """
    max_dim = max(width_in, height_in)
    min_dim = min(width_in, height_in)

    if max_dim <= 12.0:
        return CuttingMat.MAT_12X12

    if max_dim > 24.0 or min_dim > 12.0:
        print(f"  Warning: Page size {width_in:.1f}x{height_in:.1f}in may not fit on a 12x24 mat.")

    return CuttingMat.MAT_12X24


def adjust_paper_for_borderless(paper_width: str, paper_height: str) -> tuple[str, str]:
    """Adjust paper dimensions for borderless templates.

    Tells Silhouette Studio the paper is larger by BORDERLESS_EXPANSION_MM so its
    10mm minimum inset becomes an effective BORDERLESS_INSET_MM inset on the actual paper.

    Args:
        paper_width: Paper width as a unit string (e.g., "279.4mm", "11in").
        paper_height: Paper height as a unit string (e.g., "215.9mm", "8.5in").

    Returns:
        (adjusted_width, adjusted_height) as unit strings with BORDERLESS_EXPANSION_MM added to each dimension.
    """
    width_mm = size_convert.size_to_mm(paper_width)
    height_mm = size_convert.size_to_mm(paper_height)

    return f"{width_mm + BORDERLESS_EXPANSION_MM}mm", f"{height_mm + BORDERLESS_EXPANSION_MM}mm"


# =============================================================================
# Utility Functions
# =============================================================================

def type_in_field(value: str):
    """Select all text in the focused field and type a new value.

    Uses double-click to select the field contents (Ctrl+A doesn't
    work because Silhouette Studio interprets it as Select All objects).
    The mouse must already be positioned on the field.
    """
    pyautogui.doubleClick()
    pyautogui.write(str(value))
    pyautogui.press('enter')

    # Repeat to ensrure the value is entered correctly
    pyautogui.doubleClick()
    pyautogui.write(str(value))
    pyautogui.press('enter')
    pyautogui.doubleClick()
    pyautogui.write(str(value))

    pyautogui.press('enter')
    time.sleep(ACTION_DELAY)


def set_clipboard(text: str):
    """Set clipboard text (Windows)."""
    subprocess.run(['clip'], input=text.encode('utf-16-le'), check=True)


def paste():
    """Paste from clipboard."""
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(SETTLE_DELAY)


def load_calibration(filepath: Path = None) -> Optional[dict]:
    """Load calibration data from JSON file.

    If no filepath given, uses the default CALIBRATION_FILE.
    """
    if filepath is None:
        filepath = CALIBRATION_FILE
    if not filepath.exists():
        return None

    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        print(f"Loaded calibration: {filepath.name}")
        return data
    except Exception as e:
        print(f"Warning: Could not load calibration: {e}")
        return None


def save_calibration(data: dict, filepath: Path):
    """Save calibration data to JSON file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"\nCalibration saved to: {filepath}")


def connect_and_resize_studio(studio_path: str = DEFAULT_STUDIO_PATH):
    """
    Connect to a running Silhouette Studio and resize it.

    Uses pywinauto's win32 backend which supports move_window().
    Returns (window_wrapper, window_rect_dict).
    """
    app = Application(backend="win32").connect(path=studio_path, timeout=30)
    window = app.window(title_re=".*Silhouette Studio.*")
    window.restore()
    time.sleep(ACTION_DELAY)
    window.move_window(
        x=WINDOW_X, y=WINDOW_Y,
        width=WINDOW_WIDTH, height=WINDOW_HEIGHT
    )
    time.sleep(ACTION_DELAY)

    rect = window.rectangle()
    window_rect = {
        "x": rect.left,
        "y": rect.top,
        "width": rect.width(),
        "height": rect.height()
    }
    print(f"Window set to {window_rect['width']}x{window_rect['height']} "
          f"at ({window_rect['x']}, {window_rect['y']})")
    return window, window_rect


def start_and_resize_studio(studio_path: str = DEFAULT_STUDIO_PATH):
    """
    Start Silhouette Studio and resize it to a fixed window size.

    Returns (window_wrapper, window_rect_dict).
    """
    print("Starting Silhouette Studio...")

    if not os.path.exists(studio_path):
        raise FileNotFoundError(f"Not found: {studio_path}")

    subprocess.Popen([studio_path])
    startup_wait = 2 * LONG_DELAY
    print(f"Waiting {startup_wait}s for startup...")
    time.sleep(startup_wait)

    return connect_and_resize_studio(studio_path)


# =============================================================================
# Silhouette Studio Automation
# =============================================================================

class SilhouetteAutomation:
    """
    Automates Silhouette Studio operations.

    Uses pyautogui for mouse/keyboard input (clicking, typing, shortcuts).
    Uses pywinauto (win32 backend) for window management (positioning, resizing).

    All click coordinates are window-relative, loaded from a calibration JSON file.
    The actual window position is queried before each click so that coordinates
    remain correct even if the window has been moved.
    """

    def __init__(self, studio_path: str = DEFAULT_STUDIO_PATH, calibration_file: Path = None,
                 action_delay: float = ACTION_DELAY):
        self.studio_path = studio_path
        self.window = None  # pywinauto window wrapper
        self.action_delay = action_delay

        # Load calibration if available
        self.calibration = load_calibration(calibration_file)
        if self.calibration:
            print(f"Calibrated for Silhouette Studio {self.calibration.get('silhouette_studio_version', 'unknown')}")
        else:
            print("No calibration file found.")
            print("Run 'calibrate' command first.")

    def get_window_origin(self):
        """Get the current top-left corner of the Silhouette Studio window."""
        if self.window:
            rect = self.window.rectangle()
            return rect.left, rect.top
        return 0, 0

    def start(self):
        """Start Silhouette Studio with fixed window size and configure DXF import."""
        print("Starting Silhouette Studio...")

        if not os.path.exists(self.studio_path):
            raise FileNotFoundError(f"Not found: {self.studio_path}")

        subprocess.Popen([self.studio_path])
        startup_wait = 2 * LONG_DELAY
        print(f"Waiting {startup_wait}s for startup...")
        time.sleep(startup_wait)

        self.window, _ = connect_and_resize_studio(self.studio_path)

        self.set_dxf_import_asis()

    def close(self):
        """Close Silhouette Studio."""
        print("Closing Silhouette Studio...")
        pyautogui.hotkey('alt', 'F4')
        time.sleep(self.action_delay)
        pyautogui.press('n')  # Don't save
        time.sleep(self.action_delay)

    def click(self, x: int, y: int, button: str = 'left'):
        """Click at window-relative coordinates.

        Queries the current window position so clicks remain correct
        even if the window has been moved.
        """
        win_x, win_y = self.get_window_origin()
        abs_x = win_x + x
        abs_y = win_y + y
        pyautogui.click(abs_x, abs_y, button=button)
        time.sleep(self.action_delay)

    def click_element(self, element_id: str, button: str = 'left'):
        """
        Click a calibrated element by ID.

        Reads window-relative coordinates from the calibration JSON.
        """
        if self.calibration and element_id in self.calibration.get("elements", {}):
            elem = self.calibration["elements"][element_id]
            x = elem["relative"]["x"]
            y = elem["relative"]["y"]
            self.click(x, y, button=button)
            return True
        else:
            print(f"Warning: Element '{element_id}' not calibrated. Run 'calibrate' first.")
            return False

    # -------------------------------------------------------------------------
    # Preferences
    # -------------------------------------------------------------------------

    def set_dxf_import_asis(self):
        """Set DXF import mode to 'As-is' in Silhouette Studio preferences.

        Opens Edit > Preferences (Ctrl+K), navigates to the Import tab,
        changes the DXF Open setting to 'As-is', and closes the dialog.
        This preserves original DXF dimensions on import.
        """
        print("Setting DXF import to As-is...")

        pyautogui.hotkey('ctrl', 'k')
        time.sleep(self.action_delay)

        self.click_element("pref_import_tab")
        time.sleep(self.action_delay)

        self.click_element("pref_dxf_open_dropdown")
        time.sleep(self.action_delay)

        self.click_element("pref_dxf_asis")
        time.sleep(self.action_delay)

        self.click_element("pref_ok")
        time.sleep(self.action_delay)

    # -------------------------------------------------------------------------
    # File Operations
    # -------------------------------------------------------------------------

    def open_file(self, filepath: str):
        """Open a DXF file."""
        filepath = os.path.abspath(filepath)
        print(f"Opening: {filepath}")

        pyautogui.hotkey('ctrl', 'o')
        time.sleep(self.action_delay * 2)

        # Type path into the file dialog
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(SETTLE_DELAY)
        set_clipboard(filepath)
        paste()
        time.sleep(self.action_delay)

        pyautogui.press('enter')
        # Wait for Silhouette Studio to fully load the DXF
        print(f"  Waiting {LONG_DELAY}s for file to load...")
        time.sleep(LONG_DELAY)

    def save_as(self, output_path: str):
        """Save as .studio3 file."""
        output_path = os.path.abspath(output_path)
        if not output_path.lower().endswith('.studio3'):
            output_path = os.path.splitext(output_path)[0] + '.studio3'

        print(f"Saving: {output_path}")

        pyautogui.hotkey('ctrl', 'shift', 's')
        time.sleep(self.action_delay * 2)

        # Type path into the save dialog
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(SETTLE_DELAY)
        set_clipboard(output_path)
        paste()
        time.sleep(self.action_delay)

        pyautogui.press('enter')
        time.sleep(LONG_DELAY)

        # Handle overwrite confirmation
        pyautogui.press('y')
        time.sleep(LONG_DELAY)

        # Close the file to avoid accumulating open tabs
        pyautogui.hotkey('ctrl', 'w')
        time.sleep(self.action_delay)

    def new_document(self):
        """Create new document (discard current)."""
        pyautogui.hotkey('ctrl', 'n')
        time.sleep(self.action_delay)
        pyautogui.press('n')  # Don't save
        time.sleep(self.action_delay)

    # -------------------------------------------------------------------------
    # Page Setup
    # -------------------------------------------------------------------------

    def is_constrain_media_checked(self) -> bool:
        """Detect whether 'Constrain Media to Cutting Mat' is currently checked.

        Takes a screenshot of the checkbox region and computes pixel variance.
        The calibration JSON stores unchecked_variance and checked_variance as
        reference thresholds; variance above the midpoint indicates checked.
        Returns False (unchecked) if the element is not calibrated.
        """
        elem = self.calibration and self.calibration.get("elements", {}).get("constrain_media_checkbox")
        if not elem:
            print("  Warning: constrain_media_checkbox not calibrated; assuming unchecked.")
            return False

        win_x, win_y = self.get_window_origin()
        cx = win_x + elem["relative"]["x"]
        cy = win_y + elem["relative"]["y"]
        region_size = 20
        screenshot = pyautogui.screenshot(region=(cx - region_size // 2, cy - region_size // 2, region_size, region_size))
        pixels = list(screenshot.getdata())
        gray = [(r + g + b) / 3 for r, g, b in pixels]
        mean = sum(gray) / len(gray)
        variance = sum((v - mean) ** 2 for v in gray) / len(gray)

        unchecked_var = elem.get("unchecked_variance", 0.2)
        checked_var = elem.get("checked_variance", 2443.0)
        threshold = (unchecked_var + checked_var) / 2
        return variance > threshold

    def setup_page(self, mat: CuttingMat, width_in: float, height_in: float, orientation: Orientation,
                   keep_constrained: bool = True):
        """Configure page setup in four steps: cutting mat, mat dimensions, orientation, paper dimensions.

        Sets the media size to the cutting mat's maximum dimensions before
        applying orientation, then sets the actual paper dimensions afterward.
        This order makes the portrait/landscape buttons behave predictably.
        Opens the Page Setup panel once and performs all configuration
        in sequence to avoid toggling the panel open/closed.

        Args:
            mat: Cutting mat size (12x12 or 12x24).
            width_in: Page width in the display unit.
            height_in: Page height in the display unit.
            orientation: Page orientation (portrait or landscape).
            keep_constrained: Whether to leave "Constrain Media to Cutting Mat" ON.
                Should be False only for borderless 12x12 templates, where the virtual
                paper may exceed the mat but square mat orientation doesn't matter.
                See GitHub issue #136.
        """
        print(f"  Setting up page: {mat.value} mat, {width_in:.2f}x{height_in:.2f}, {orientation.value}, keep_constrained={keep_constrained}")

        # Open the Page Setup panel once
        self.click_element("page_setup")
        time.sleep(ACTION_DELAY)

        # Enable constrain so mat, media size, and orientation behave predictably.
        if not self.is_constrain_media_checked():
            print("  Enabling Constrain Media to Cutting Mat...")
            self.click_element("constrain_media_checkbox")

        # Select cutting mat (12x12 or 12x24).
        self.click_element("cutting_mat_dropdown")
        if mat == CuttingMat.MAT_12X12:
            self.click_element("cutting_mat_12x12")
        else:
            self.click_element("cutting_mat_12x24")

        # Set media size to the cutting mat's maximum dimensions before applying
        # orientation. The portrait/landscape buttons behave unpredictably depending
        # on the current media size — they may swap dimensions or do nothing.
        # Using a known square (or max-landscape) starting size makes the
        # orientation button reliably produce the expected result.
        # Note: the 12x24 option only appears in the dropdown when the 12x24
        # cutting mat is selected.
        self.click_element("media_size_dropdown")
        if mat == CuttingMat.MAT_12X12:
            self.click_element("media_size_12x12")
        else:
            self.click_element("media_size_12x24")

        # Set orientation
        if orientation == Orientation.PORTRAIT:
            self.click_element("portrait_button")
        else:
            self.click_element("landscape_button")

        # Conditionally disable constrain after setting orientation.
        # TODO (#136): Remove this once all templates use unconstrained mode with
        # portrait mat orientation, which is consistent across all mat types.
        if not keep_constrained:
            print("  Disabling Constrain Media to Cutting Mat...")
            self.click_element("constrain_media_checkbox")

        # Set actual paper dimensions
        self.click_element("media_width_field")
        type_in_field(f"{width_in:.2f}")

        self.click_element("media_height_field")
        type_in_field(f"{height_in:.2f}")

    # -------------------------------------------------------------------------
    # Transform / Centering
    # -------------------------------------------------------------------------

    def select_all_and_group(self):
        """Select all objects and group them."""
        print("  Selecting all and grouping...")
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(self.action_delay)
        pyautogui.hotkey('ctrl', 'g')
        time.sleep(self.action_delay)

    def center_to_page(self):
        """Center the selected object(s) to the page."""
        print("  Centering to page...")

        self.select_all_and_group()
        self.click_element("transform")
        time.sleep(ACTION_DELAY)
        self.click_element("center_to_page")
        self.ungroup_all()

    def ungroup_all(self):
        """Select all and ungroup (Ctrl+A, Ctrl+Shift+G)."""
        print("  Ungrouping...")
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(self.action_delay)
        pyautogui.hotkey('ctrl', 'shift', 'g')
        time.sleep(self.action_delay)

    def flip_vertically(self):
        """Select all objects and flip them vertically via the right-click context menu.

        Corrects SS's image-fill mirroring on closed-polyline shapes (see
        add_rounded_rectangle() in dxf_manager.py). Also mirrors the cutting
        path, harmless today since shapes are symmetric (single uniform
        corner radius).
        """
        print("  Flipping vertically...")
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(self.action_delay)
        self.click_element("cutting_path_menu", button='right')
        self.click_element("context_flip_vertically")

    # def release_compound_path(self):
    #     """Select all and release compound path (Ctrl+A, Ctrl+Shift+E).

    #     When a DXF is imported with LINE+ARC entities, Silhouette Studio merges
    #     all entities into a single compound path regardless of DXF layers or groups.
    #     Ctrl+Shift+E releases the compound path into individually selectable card paths.
    #     This must be called after ungrouping so the compound path is the selected object.
    #     """
    #     print("  Releasing compound path...")
    #     pyautogui.hotkey('ctrl', 'a')
    #     time.sleep(self.action_delay)
    #     pyautogui.hotkey('ctrl', 'shift', 'e')
    #     time.sleep(self.action_delay)

    # -------------------------------------------------------------------------
    # Registration Marks
    # -------------------------------------------------------------------------

    def set_registration_marks(self, settings: RegistrationSettings):
        """Configure registration mark settings."""
        print(f"  Setting registration marks: enabled={settings.enabled}")

        self.click_element("print_cut")
        time.sleep(ACTION_DELAY)

        # Enable registration marks
        self.click_element("regmark_checkbox")
        time.sleep(self.action_delay)

        if settings.enabled:
            # Set length
            self.click_element("regmark_length_field")
            type_in_field(str(settings.length))

            # Set thickness
            self.click_element("regmark_thickness_field")
            type_in_field(str(settings.thickness))

            # Set inset
            self.click_element("regmark_inset_field")
            type_in_field(str(settings.inset))

    # -------------------------------------------------------------------------
    # Full Conversion Workflow
    # -------------------------------------------------------------------------

    def convert(
        self,
        input_dxf: str,
        output_studio3: str,
        paper_width: str,
        paper_height: str,
        unit: Unit,
        orientation: Orientation = Orientation.LANDSCAPE,
        center: bool = True,
        registration: Optional[RegistrationSettings] = None,
        borderless: bool = False
    ):
        """
        Full conversion workflow:
        1. Open DXF
        2. Page setup (cutting mat, media size, orientation, dimensions)
        3. Center paths
        4. Flip vertically (corrects the image-fill mirror on closed-polyline shapes)
        5. Set registration marks
        6. Save as .studio3

        Args:
            input_dxf: Path to the input DXF file.
            output_studio3: Path for the output .studio3 file.
            paper_width: Paper width as a unit string (e.g. "11in", "297mm").
            paper_height: Paper height as a unit string (e.g. "8.5in", "210mm").
            unit: Unit for all numeric values ("mm" or "in"). Must match Silhouette Studio's unit setting.
            orientation: Page orientation (portrait or landscape).
            center: Whether to center paths on the page.
            registration: Registration mark settings in the specified unit, or None to skip.
        """
        print(f"\nConverting: {input_dxf}")

        self.open_file(input_dxf)

        # Convert page dimensions to the specified unit for Silhouette Studio.
        # layouts.json stores paper sizes as landscape (width > height).
        # For portrait, swap so width < height matches Silhouette Studio's expectation.
        if unit == Unit.MM:
            width_value = size_convert.size_to_mm(paper_width)
            height_value = size_convert.size_to_mm(paper_height)
        else:  # unit == Unit.IN
            width_value = size_convert.size_to_in(paper_width)
            height_value = size_convert.size_to_in(paper_height)

        if orientation == Orientation.PORTRAIT:
            width_value, height_value = height_value, width_value

        # Configure page setup (mat, media size, orientation, dimensions) in one pass
        # Note: determine_cutting_mat expects inches for mat selection
        width_in = size_convert.size_to_in(paper_width)
        height_in = size_convert.size_to_in(paper_height)
        if orientation == Orientation.PORTRAIT:
            width_in, height_in = height_in, width_in
        mat = determine_cutting_mat(width_in, height_in)
        # See GitHub issue #136. TODO (#136): Remove this distinction once all templates
        # use unconstrained mode with portrait mat orientation.
        keep_constrained = not (borderless and mat == CuttingMat.MAT_12X12)
        self.setup_page(mat, width_value, height_value, orientation, keep_constrained=keep_constrained)

        if center:
            self.center_to_page()

        self.flip_vertically()

        if registration:
            self.set_registration_marks(registration)

        self.save_as(output_studio3)

        print("  Done!")


# =============================================================================
# Calibration
# =============================================================================

# Elements to calibrate, grouped by which panel they belong to.
# The user is guided through each panel in sequence so they only
# need to open each sidebar tool once.
CALIBRATION_ELEMENTS = [
    # --- Preferences (Ctrl+K) ---
    {
        "id": "pref_import_tab",
        "name": "Import tab in Preferences",
        "description": "Press Ctrl+K to open Preferences. "
                       "Click the 'Import' tab/button."
    },
    {
        "id": "pref_dxf_open_dropdown",
        "name": "DXF Open dropdown",
        "description": "In the Import tab, find the 'Open' dropdown for DXF files. "
                       "Click the dropdown to expand it."
    },
    {
        "id": "pref_dxf_asis",
        "name": "As-is option for DXF Open",
        "description": "The DXF Open dropdown should be expanded. "
                       "Click the 'As-is' option."
    },
    {
        "id": "pref_ok",
        "name": "OK button in Preferences",
        "description": "Click the OK button to close the Preferences dialog."
    },
    # --- Page Setup ---
    {
        "id": "page_setup",
        "name": "Page Setup icon in sidebar",
        "description": "Click the Page Setup tool icon in the left sidebar"
    },
    {
        "id": "cutting_mat_dropdown",
        "name": "Cutting mat dropdown",
        "description": "The Page Setup panel should now be open. "
                       "Click the dropdown that selects the cutting mat size."
    },
    {
        "id": "cutting_mat_12x12",
        "name": "12x12 cutting mat option",
        "description": "The cutting mat dropdown should be open. "
                       "Click the 12\" x 12\" option."
    },
    {
        "id": "cutting_mat_12x24",
        "name": "12x24 cutting mat option",
        "description": "The cutting mat dropdown should be open. "
                       "Click the 12\" x 24\" option."
    },
    {
        "id": "media_size_dropdown",
        "name": "Media size dropdown",
        "description": "Click the dropdown that selects the media/page size."
    },
    {
        "id": "media_size_12x12",
        "name": "12x12 media size option",
        "description": "The 12x12 cutting mat must be selected and the media size dropdown should be open. "
                       "Click the 12\" x 12\" option."
    },
    {
        "id": "media_size_12x24",
        "name": "12x24 media size option",
        "description": "The 12x24 cutting mat must be selected and the media size dropdown should be open. "
                       "Click the 12\" x 24\" option."
    },
    {
        "id": "media_width_field",
        "name": "Media width input field",
        "description": "Click the numerical input field for custom media width."
    },
    {
        "id": "media_height_field",
        "name": "Media height input field",
        "description": "Click the numerical input field for custom media height."
    },
    {
        "id": "portrait_button",
        "name": "Portrait orientation button",
        "description": "Click the portrait orientation button."
    },
    {
        "id": "landscape_button",
        "name": "Landscape orientation button",
        "description": "Click the landscape orientation button."
    },
    # --- Transform ---
    {
        "id": "transform",
        "name": "Transform icon in sidebar",
        "description": "Click the Transform panel icon in the left sidebar"
    },
    {
        "id": "center_to_page",
        "name": "Center to Page button",
        "description": "The Transform panel should be open. "
                       "Click the Center to Page button."
    },
    # --- Print & Cut ---
    {
        "id": "print_cut",
        "name": "Print & Cut icon in sidebar",
        "description": "Click the Print & Cut (registration marks) panel icon in the left sidebar"
    },
    {
        "id": "regmark_checkbox",
        "name": "Registration marks enable checkbox",
        "description": "The Print & Cut panel should be open. "
                       "Click the checkbox to enable registration marks."
    },
    {
        "id": "regmark_length_field",
        "name": "Registration mark length input field",
        "description": "The Print & Cut panel should be open. "
                       "Click the numerical input field for mark length"
    },
    {
        "id": "regmark_thickness_field",
        "name": "Registration mark thickness input field",
        "description": "The Print & Cut panel should be open. "
                       "Click the numerical input field for mark thickness"
    },
    {
        "id": "regmark_inset_field",
        "name": "Registration mark inset input field",
        "description": "The Print & Cut panel should be open. "
                       "Click the numerical input field for mark inset"
    },
    # --- Flip Vertically (right-click context menu) ---
    {
        "id": "cutting_path_menu",
        "name": "Open cutting path menu (right-click)",
        "description": "Select on any cutting path on the canvas "
                       "(used as the target for the right-click context menu)."
                       "Right click anywhere to open the context menu."
    },
    {
        "id": "context_flip_vertically",
        "name": "Flip Vertically option in context menu",
        "description": "The cutting path context menu should be open. "
                       "Click the 'Flip Vertically' option."
    },
]


# =============================================================================
# Batch Conversion Helpers
# =============================================================================

def parse_dxf_filename(filename: str, config: LayoutConfig) -> tuple[str, str, Variant] | None:
    """Extract paper_size, card_size, and variant from a DXF filename.

    Expected formats:
      - {paper_size}-{card_size}-v{N}.dxf (default variant)
      - {paper_size}-{card_size}-borderless-v{N}.dxf (borderless variant)

    Card sizes may contain underscores (e.g. poker_half, bridge_square).
    Returns (paper_size, card_size, variant) or None if parsing fails.
    """
    stem = Path(filename).stem

    for paper_size in config.paper_sizes:
        if stem.startswith(paper_size + "-"):
            remainder = stem[len(paper_size) + 1:]
            # Strip version suffix (-v1, -v2, etc.)
            remainder_no_version = re.sub(r"-v\d+$", "", remainder)

            # Check for borderless variant
            if remainder_no_version.endswith("-borderless"):
                card_size = remainder_no_version[:-len("-borderless")]
                variant = Variant.BORDERLESS
            else:
                card_size = remainder_no_version
                variant = Variant.DEFAULT

            # Verify the layout exists
            if (paper_size in config.layouts and
                card_size in config.layouts[paper_size] and
                variant.value in config.layouts[paper_size][card_size]):
                return paper_size, card_size, variant

    return None


def get_paper_dimensions(paper_size: str | None, config: LayoutConfig) -> tuple[str, str]:
    """Get paper width and height unit strings for a paper size.

    Falls back to letter size if paper_size is None or unknown.
    """
    if paper_size is not None and paper_size in config.paper_sizes:
        paper_def = config.paper_sizes[paper_size]
        return paper_def.width, paper_def.height

    paper_def = config.paper_sizes["letter"]
    return paper_def.width, paper_def.height


def get_orientation_for_dxf(paper_size: str | None, card_size: str | None, variant: Variant | None, config: LayoutConfig) -> Orientation:
    """Look up the paper orientation for a paper/card/variant combination from layouts.json.

    Falls back to landscape if any parameter is None.
    """
    if paper_size is not None and card_size is not None and variant is not None:
        return config.layouts[paper_size][card_size][variant.value].orientation

    return Orientation.LANDSCAPE


def get_max_length_for_dxf(paper_size: str | None, card_size: str | None, variant: Variant | None, config: LayoutConfig, unit: Unit) -> float | None:
    """Look up the max registration mark length for a paper/card/variant combination.

    Args:
        paper_size: Paper size key (e.g. "letter"), or None.
        card_size: Card size key (e.g. "poker"), or None.
        variant: Variant enum (Variant.DEFAULT or Variant.BORDERLESS), or None.
        config: Loaded layout config.
        unit: Unit.MM or Unit.IN.

    Returns:
        Max length in the requested unit, or None if not available.
    """
    if paper_size is not None and card_size is not None and variant is not None:
        layout_reg = config.layouts[paper_size][card_size][variant.value].registration
        mm = size_convert.size_to_mm(layout_reg.length) if layout_reg is not None and layout_reg.length is not None else None
        if mm is None:
            return None
        if unit == Unit.IN:
            return round(mm / 25.4, 4)
        return mm

    return None


# =============================================================================
# CLI
# =============================================================================

layout_config = load_layout_config()
paper_size_choices = get_all_paper_size_names(layout_config)


@click.group()
def cli():
    """Convert DXF files to Silhouette Studio .studio3 format with full automation."""
    pass


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.argument("output_file", type=click.Path())
@click.option("--paper_size", type=click.Choice(paper_size_choices, case_sensitive=False), default="letter", show_default=True, help="Paper size (from layouts.json).")
@click.option("--orientation", type=click.Choice([o.value for o in Orientation], case_sensitive=False), default=Orientation.LANDSCAPE.value, show_default=True, help="Paper orientation.")
@click.option("--no_center", is_flag=True, help="Don't center paths to page.")
@click.option("--registration", is_flag=True, help="Enable registration marks.")
@click.option("--unit", type=click.Choice([u.value for u in Unit], case_sensitive=False), required=True, help="Unit for registration mark values.")
@click.option("--reg_length", type=float, default=0, show_default=True, help="Registration mark length. 0 = minimum allowed by Silhouette Studio.")
@click.option("--reg_thickness", type=float, default=0, show_default=True, help="Registration mark thickness. 0 = minimum allowed by Silhouette Studio.")
@click.option("--reg_inset", type=float, default=0, show_default=True, help="Registration mark inset. 0 = minimum allowed by Silhouette Studio.")
@click.option("--action_delay", type=float, default=ACTION_DELAY, show_default=True, help="Delay between UI actions (seconds).")
@click.option("--calibration_path", type=click.Path(), default=None, help="Path to calibration JSON.")
@click.option("--studio_path", default=DEFAULT_STUDIO_PATH, show_default=True, help="Path to Silhouette Studio executable.")
def single(input_file, output_file, paper_size, orientation, no_center, registration, unit,
           reg_length, reg_thickness, reg_inset, action_delay, calibration_path, studio_path):
    """Convert a single DXF file to .studio3 with paper size setup and registration marks."""
    unit = Unit(unit)
    orient = Orientation(orientation)
    reg_settings = None
    if registration:
        reg_settings = RegistrationSettings(
            enabled=True,
            length=reg_length,
            thickness=reg_thickness,
            inset=reg_inset
        )

    # Look up page dimensions from layouts.json
    config = load_layout_config()
    paper_size = resolve_paper_size_alias(config, paper_size)
    if paper_size not in config.paper_sizes:
        click.echo(f"Error: Unknown paper size '{paper_size}'. Available: {list(config.paper_sizes.keys())}")
        return
    paper_def = config.paper_sizes[paper_size]
    paper_width = paper_def.width
    paper_height = paper_def.height

    click.echo("=" * 60)
    click.echo("DXF to Studio3 Converter")
    click.echo("=" * 60)
    click.echo()
    click.echo(f"Paper size: {paper_size} ({paper_width} x {paper_height})")
    click.echo()
    click.echo("WARNING: Do not use mouse/keyboard during conversion!")
    click.echo("Move mouse to top-left corner to abort.")
    click.echo()

    if not click.confirm("Proceed?"):
        click.echo("Aborted.")
        return

    cal_path = Path(calibration_path) if calibration_path else None
    automation = SilhouetteAutomation(studio_path, cal_path, action_delay)

    try:
        automation.start()
        automation.convert(
            input_file,
            output_file,
            paper_width=paper_width,
            paper_height=paper_height,
            unit=unit,
            orientation=orient,
            center=not no_center,
            registration=reg_settings
        )
        click.echo("\nConversion complete!")
    except KeyboardInterrupt:
        click.echo("\nAborted by user.")
    except pyautogui.FailSafeException:
        click.echo("\nAborted - mouse moved to corner.")
    finally:
        try:
            automation.close()
        except Exception:
            pass


@cli.command()
@click.option("--studio_path", default=DEFAULT_STUDIO_PATH, show_default=True, help="Path to Silhouette Studio executable.")
def calibrate(studio_path):
    """
    Interactively calibrate UI element coordinates.

    Starts Silhouette Studio at a fixed window size, then prompts you
    to hover over each UI element and press Enter to record its position.

    Saves window-relative coordinates to assets/gui_coordinates.json.
    """
    click.echo("=" * 60)
    click.echo("UI Coordinate Calibration Tool")
    click.echo("=" * 60)
    click.echo()
    click.echo("This tool will:")
    click.echo(f"  1. Start Silhouette Studio at {WINDOW_WIDTH}x{WINDOW_HEIGHT}")
    click.echo("  2. Prompt you to hover over each UI element")
    click.echo(f"  3. Save relative coordinates to {CALIBRATION_FILE}")
    click.echo()
    click.echo("Press 's' to skip an element, Ctrl+C to abort.")
    click.echo()

    if not click.confirm("Start Silhouette Studio and begin calibration?"):
        click.echo("Aborted.")
        return

    # Start Silhouette Studio at fixed size
    _, window_rect = start_and_resize_studio(studio_path)

    output_file = CALIBRATION_FILE
    existing = load_calibration(output_file)
    existing_elements = existing.get("elements", {}) if existing else {}

    click.echo()
    version = click.prompt(
        "What version of Silhouette Studio are you using?",
        default=existing.get("silhouette_studio_version", "unknown") if existing else "unknown"
    )
    click.echo()

    click.echo(f"Calibration will be saved to: {output_file}")
    if existing_elements:
        click.echo(f"Loaded {len(existing_elements)} existing element(s); skipped elements keep their current coordinates.")
    click.echo()

    calibration = {
        "silhouette_studio_version": version,
        "window": window_rect,
        "elements": dict(existing_elements),
        "notes": "All coordinates are relative to the window top-left corner"
    }

    try:
        index = 0
        while index < len(CALIBRATION_ELEMENTS):
            element = CALIBRATION_ELEMENTS[index]
            click.echo(f"\n--- {element['name']} ---")
            click.echo(f"    {element['description']}")

            response = input("Position mouse and press Enter (or 's' to skip, 'b' to go back): ").strip().lower()

            if response == 'b':
                if index == 0:
                    click.echo("  Already at the first element.")
                else:
                    index -= 1
                    click.echo("  Going back...")
                continue

            if response == 's':
                if element["id"] in calibration["elements"]:
                    click.echo("  Skipped (kept existing coordinates)")
                else:
                    click.echo("  Skipped")
                index += 1
                continue

            pos = pyautogui.position()

            # Store as window-relative coordinates
            rel_x = pos.x - window_rect['x']
            rel_y = pos.y - window_rect['y']

            calibration["elements"][element["id"]] = {
                "name": element["name"],
                "relative": {"x": rel_x, "y": rel_y}
            }

            click.echo(f"  Recorded: relative=({rel_x}, {rel_y})")
            index += 1

    except KeyboardInterrupt:
        click.echo("\n\nCalibration interrupted.")
        if not click.confirm("Save partial calibration?", default=False):
            click.echo("Discarded.")
            return

    # Save calibration
    save_calibration(calibration, output_file)

    # Print summary
    click.echo()
    click.echo("=" * 60)
    click.echo("Calibration Summary")
    click.echo("=" * 60)
    click.echo(f"Window size: {window_rect['width']}x{window_rect['height']}")
    click.echo(f"Elements recorded: {len(calibration['elements'])}")
    click.echo()
    for elem_id, elem_data in calibration['elements'].items():
        click.echo(f"  {elem_id}: ({elem_data['relative']['x']}, {elem_data['relative']['y']})")
    click.echo()
    click.echo("Different screen sizes/DPI may require re-calibration.")


@cli.command()
@click.option("--unit", type=click.Choice([u.value for u in Unit], case_sensitive=False), required=True, help="Unit for registration mark values.")
@click.option("--studio_path", default=DEFAULT_STUDIO_PATH, show_default=True, help="Path to Silhouette Studio executable.")
@click.option("--action_delay", type=float, default=ACTION_DELAY, show_default=True, help="Delay between UI actions (seconds).")
@click.option("--calibration_path", type=click.Path(), default=None, help="Path to calibration JSON.")
@click.option("--new", "generate_new", is_flag=True, help="Only convert layouts whose .studio3 file is missing (based on layouts.json versions).")
@click.option("--dry_run", is_flag=True, help="List files that would be converted without running Silhouette Studio.")
def batch(unit, studio_path, action_delay, calibration_path, generate_new, dry_run):
    """Batch convert all DXF files in cutting_templates/ to .studio3 with registration marks."""
    unit = Unit(unit)
    out_path = TEMPLATES_DIR
    out_path.mkdir(parents=True, exist_ok=True)

    config = load_layout_config()

    if generate_new:
        # Only DXFs that actually exist in out_path are candidates - out_path may only
        # contain a subset of layouts.json's full catalog (e.g. when
        # SCM_CUTTING_TEMPLATES_DIR is redirected to a companion project's own card
        # sizes), so deriving candidates from layouts.json itself (like the old
        # implementation did) would warn about every entry that will never exist there.
        # Among the DXFs that do exist, skip ones whose .studio3 is already converted.
        all_dxf_files = sorted(list((out_path / "dxf").glob("*.dxf")) + list((out_path / "borderless" / "dxf").glob("*.dxf")))
        dxf_files = []
        for dxf_file in all_dxf_files:
            _, _, variant = parse_dxf_filename(dxf_file.name, config) or (None, None, None)
            if variant == Variant.BORDERLESS:
                studio3_file = out_path / "borderless" / dxf_file.with_suffix(".studio3").name
            else:
                studio3_file = out_path / dxf_file.with_suffix(".studio3").name
            if not studio3_file.exists():
                dxf_files.append(dxf_file)
    else:
        # Search both default and borderless DXF directories
        dxf_files = sorted(list((out_path / "dxf").glob("*.dxf")) + list((out_path / "borderless" / "dxf").glob("*.dxf")))

    if not dxf_files:
        if generate_new:
            click.echo("All .studio3 files are up to date.")
        else:
            click.echo(f"No DXF files found in cutting_templates/dxf/ or cutting_templates/borderless/dxf/")
        return

    click.echo(f"Found {len(dxf_files)} DXF files to convert")

    if dry_run:
        for dxf_file in dxf_files:
            paper_size, card_size, variant = parse_dxf_filename(dxf_file.name, config) or (None, None, None)
            orientation = get_orientation_for_dxf(paper_size, card_size, variant, config)
            paper_w, paper_h = get_paper_dimensions(paper_size, config)

            # For borderless, show the adjusted (virtual) paper size that will be used
            if variant == Variant.BORDERLESS:
                paper_w, paper_h = adjust_paper_for_borderless(paper_w, paper_h)

            max_len = get_max_length_for_dxf(paper_size, card_size, variant, config, unit)
            len_str = f", max_length={max_len}{unit.value}" if max_len is not None else ""
            click.echo(f"  {dxf_file.name} ({orientation.value}, {paper_w} x {paper_h}{len_str})")
        click.echo()
        click.echo(f"Registration mark unit: {unit.value}")
        click.echo()
        click.echo("Dry run complete. No files were converted.")
        return

    for dxf_file in dxf_files:
        click.echo(f"  {dxf_file.name}")
    click.echo()
    click.echo(f"Registration mark unit: {unit.value}")
    click.echo()

    click.echo("=" * 60)
    click.echo("Batch DXF to Studio3 Converter")
    click.echo("=" * 60)
    click.echo()
    click.echo("WARNING: Do not use mouse/keyboard during conversion!")
    click.echo("Move mouse to top-left corner to abort.")
    click.echo()

    if not click.confirm("Proceed?"):
        click.echo("Aborted.")
        return

    cal_path = Path(calibration_path) if calibration_path else None
    automation = SilhouetteAutomation(studio_path, cal_path, action_delay)

    try:
        automation.start()

        converted = 0
        errors = 0

        for dxf_file in dxf_files:
            paper_size, card_size, variant = parse_dxf_filename(dxf_file.name, config) or (None, None, None)
            # Borderless templates go in borderless/ subdirectory
            if variant == Variant.BORDERLESS:
                output_file = out_path / "borderless" / dxf_file.with_suffix(".studio3").name
                (out_path / "borderless").mkdir(parents=True, exist_ok=True)
            else:
                output_file = out_path / dxf_file.with_suffix(".studio3").name
            orientation = get_orientation_for_dxf(paper_size, card_size, variant, config)
            paper_w, paper_h = get_paper_dimensions(paper_size, config)
            max_len = get_max_length_for_dxf(paper_size, card_size, variant, config, unit)

            # For borderless templates, adjust paper size to trick Silhouette Studio
            # into using a smaller effective inset (by using 10mm inset on larger virtual paper)
            if variant == Variant.BORDERLESS:
                virtual_w, virtual_h = adjust_paper_for_borderless(paper_w, paper_h)
                # Skip if the virtual paper size exceeds the 12x24 mat (see GitHub issue #136).
                # TODO (#136): Remove this skip once templates use unconstrained mode.
                mat_check = determine_cutting_mat(size_convert.size_to_in(paper_w), size_convert.size_to_in(paper_h))
                if mat_check == CuttingMat.MAT_12X24:
                    vw_in = size_convert.size_to_in(virtual_w)
                    vh_in = size_convert.size_to_in(virtual_h)
                    if min(vw_in, vh_in) > 12.0 or max(vw_in, vh_in) > 24.0:
                        click.echo(f"  Skipping {dxf_file.name}: virtual paper exceeds 12x24 mat (see GitHub issue #136)")
                        continue
                paper_w, paper_h = virtual_w, virtual_h

            # Convert registration mark values to the specified unit
            # Inset: always MIN_REG_INSET_MM (Silhouette Studio's minimum)
            inset_value = page_manager.MIN_REG_INSET_MM if unit == Unit.MM else page_manager.MIN_REG_INSET_MM / 25.4
            thickness_value = page_manager.MAX_REG_THICKNESS_MM if unit == Unit.MM else page_manager.MAX_REG_THICKNESS_MM / 25.4

            # Registration marks: always enabled, thickness and inset in specified unit,
            # length set to the computed max for this layout (already in correct unit)
            reg_settings = RegistrationSettings(
                enabled=True,
                length=max_len if max_len is not None else 0,
                thickness=thickness_value,
                inset=inset_value,
            )

            try:
                automation.convert(
                    input_dxf=str(dxf_file),
                    output_studio3=str(output_file),
                    paper_width=paper_w,
                    paper_height=paper_h,
                    unit=unit,
                    orientation=orientation,
                    center=True,
                    registration=reg_settings,
                    borderless=(variant == Variant.BORDERLESS),
                )
                converted += 1
            except Exception as e:
                click.echo(f"  Error converting {dxf_file.name}: {e}")
                errors += 1

        click.echo()
        click.echo(f"Converted {converted} files ({errors} errors)")

    except KeyboardInterrupt:
        click.echo("\nAborted by user.")
    except Exception as e:
        click.echo(f"\nFail-safe triggered: {e}")
    finally:
        try:
            automation.close()
        except Exception:
            pass


if __name__ == "__main__":
    cli()
