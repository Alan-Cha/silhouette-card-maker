#!/usr/bin/env python3
"""
Print and Play (PnP) PDF Extractor

Extracts card images from PnP game PDFs and organizes them into
front, back, and double-sided directories for processing.

IDEAL PDF STRUCTURE (Alternating Pages)
========================================
┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐
│ Page 1  │  │ Page 2  │  │ Page 3  │  │ Page 4  │
│ FRONTS  │  │ BACKS   │  │ FRONTS  │  │ BACKS   │
│┌──┬──┬──┐│  │┌──┬──┬──┐│  │┌──┬──┬──┐│  │┌──┬──┬──┐│
││1 │2 │3 ││  ││1 │2 │3 ││  ││7 │8 │9 ││  ││7 │8 │9 ││
│├──┼──┼──┤│  │├──┼──┼──┤│  │├──┼──┼──┤│  │├──┼──┼──┤│
││4 │5 │6 ││  ││4 │5 │6 ││  ││10│11│12││  ││10│11│12││
│└──┴──┴──┘│  │└──┴──┴──┘│  │└──┴──┴──┘│  │└──┴──┴──┘│
└─────────┘  └─────────┘  └─────────┘  └─────────┘

COMMON BACK DETECTION
=====================
Back pages scanned → Count image occurrences
  ┌────────────────────────────────────┐
  │ xref=181: 21 times → COMMON BACK   │ → game/back/back_1.png
  │ xref=186:  5 times → COMMON BACK   │ → game/back/back_2.png
  │ xref=004:  1 time  → UNIQUE        │ → game/double_sided/
  └────────────────────────────────────┘

FOLDER MODE (Front/Back PDF Pairs)
==================================
Chain Mail PNP/
├── CharactersFront.pdf  ─┐
├── CharactersBack.pdf   ─┴→ Paired
├── ResourcesFront.pdf   ─┐
├── ResourcesBack.pdf    ─┴→ Paired
└── RulesInside.pdf      ─→ Skipped (no cards)
"""

import os
import re
from collections import Counter
from typing import Dict, List, Optional, Set, Tuple

import click
import fitz  # PyMuPDF

# Output directories
FRONT_DIR = os.path.join("game", "front")
BACK_DIR = os.path.join("game", "back")
DOUBLE_SIDED_DIR = os.path.join("game", "double_sided")

# Minimum image dimension to be considered a card (filters out logos, icons)
MIN_CARD_DIMENSION = 200

# Threshold for common back detection (must appear this many times)
COMMON_BACK_THRESHOLD = 10


def ensure_directories(subdir: str = ""):
    """Create output directories if they don't exist."""
    for base_dir in [FRONT_DIR, BACK_DIR, DOUBLE_SIDED_DIR]:
        dir_path = os.path.join(base_dir, subdir) if subdir else base_dir
        os.makedirs(dir_path, exist_ok=True)


def parse_skip_pages(skip_str: str) -> Set[int]:
    """
    Parse skip pages specification into a set of page numbers.

    Args:
        skip_str: Comma-separated list of pages and ranges (e.g., "1,3-5,7")

    Returns:
        Set of 1-indexed page numbers to skip
    """
    pages = set()
    if not skip_str:
        return pages

    for part in skip_str.split(","):
        part = part.strip()
        if not part:
            continue

        if "-" in part:
            # Range specification
            try:
                start, end = part.split("-", 1)
                start, end = int(start.strip()), int(end.strip())
                pages.update(range(start, end + 1))
            except ValueError:
                print(f"Warning: Invalid range '{part}', skipping")
        else:
            # Single page
            try:
                pages.add(int(part))
            except ValueError:
                print(f"Warning: Invalid page number '{part}', skipping")

    return pages


def get_card_images_from_page(
    doc: fitz.Document,
    page: fitz.Page,
    min_dimension: int = MIN_CARD_DIMENSION
) -> List[dict]:
    """
    Extract card-sized images from a page with their positions.

    Returns a list of dicts with keys: xref, width, height, x, y, image_bytes, ext
    Sorted by position (top-to-bottom, left-to-right).
    """
    cards = []

    for img in page.get_images(full=True):
        xref = img[0]
        base_image = doc.extract_image(xref)
        width = base_image["width"]
        height = base_image["height"]

        # Filter out small images (logos, icons)
        if width < min_dimension or height < min_dimension:
            continue

        # Get all positions where this image appears on the page
        rects = page.get_image_rects(xref)
        for rect in rects:
            x0, y0, _, _ = rect

            # Filter out images in header/footer area (top 15% or bottom 5%)
            page_height = page.rect.height
            if y0 < page_height * 0.10:  # Header area
                continue

            cards.append({
                "xref": xref,
                "width": width,
                "height": height,
                "x": x0,
                "y": y0,
                "image_bytes": base_image["image"],
                "ext": base_image["ext"]
            })

    # Sort by position: top-to-bottom (y), then left-to-right (x)
    # Use a tolerance for y-coordinate to group rows
    y_tolerance = 20
    cards.sort(key=lambda c: (round(c["y"] / y_tolerance) * y_tolerance, c["x"]))

    return cards


def detect_grid_size(cards: List[dict], tolerance: float = 30) -> Tuple[int, int]:
    """
    Auto-detect grid size from card positions.

    Returns (columns, rows) tuple.
    """
    if not cards:
        return (0, 0)

    # Group by rows using y-coordinate clustering
    rows = []
    current_row = [cards[0]]
    current_y = cards[0]["y"]

    for card in cards[1:]:
        if abs(card["y"] - current_y) < tolerance:
            current_row.append(card)
        else:
            rows.append(current_row)
            current_row = [card]
            current_y = card["y"]
    rows.append(current_row)

    num_rows = len(rows)
    num_cols = max(len(row) for row in rows) if rows else 0

    return (num_cols, num_rows)


def save_image(image_bytes: bytes, ext: str, output_path: str) -> str:
    """Save image bytes to file."""
    # Normalize extension
    if ext == "jpeg":
        ext = "jpg"

    full_path = f"{output_path}.{ext}"
    with open(full_path, "wb") as f:
        f.write(image_bytes)

    return full_path


def scan_back_pages_for_common_backs(
    doc: fitz.Document,
    skip_pages: Set[int],
    min_dimension: int,
    single_sided: bool
) -> Counter:
    """
    Scan all back pages and count xref occurrences.

    Returns a Counter of xref -> count for back page images.
    """
    xref_counts = Counter()

    if single_sided:
        return xref_counts

    total_pages = len(doc)

    for page_num in range(total_pages):
        page_display = page_num + 1
        is_back_page = (page_num % 2 == 1)  # Odd 0-indexed = back

        if not is_back_page:
            continue

        if page_display in skip_pages:
            continue

        page = doc[page_num]
        cards = get_card_images_from_page(doc, page, min_dimension)

        for card in cards:
            xref_counts[card["xref"]] += 1

    return xref_counts


def process_pdf(
    pdf_path: str,
    grid: Optional[str] = None,
    short_edge_flip: bool = False,
    min_dimension: int = MIN_CARD_DIMENSION,
    skip_pages: Optional[Set[int]] = None,
    single_sided: bool = False,
    common_back: bool = True,
    output_subdir: str = "",
    filename_prefix: str = ""
) -> None:
    """
    Process a PnP PDF and extract card images.

    Args:
        pdf_path: Path to the PDF file
        grid: Optional grid size override (e.g., "3x3")
        short_edge_flip: If True, reverse position order on back pages
        min_dimension: Minimum dimension for card images
        skip_pages: Set of page numbers to skip (1-indexed)
        single_sided: If True, treat all pages as fronts
        common_back: If True, detect and consolidate common backs
        output_subdir: Subdirectory for output (for folder processing)
        filename_prefix: Prefix for output filenames
    """
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    skip_pages = skip_pages or set()
    ensure_directories(output_subdir)

    doc = fitz.open(pdf_path)
    total_pages = len(doc)

    print(f"Processing: {pdf_path}")
    print(f"Total pages: {total_pages}")
    if skip_pages:
        print(f"Skipping pages: {sorted(skip_pages)}")
    if single_sided:
        print("Mode: Single-sided (all pages treated as fronts)")

    # Parse grid override if provided
    grid_cols, grid_rows = None, None
    if grid:
        try:
            parts = grid.lower().split("x")
            grid_cols, grid_rows = int(parts[0]), int(parts[1])
            print(f"Using grid override: {grid_cols}x{grid_rows}")
        except (ValueError, IndexError):
            print(f"Warning: Invalid grid format '{grid}', using auto-detection")

    # Common back detection: First pass - scan back pages
    common_backs: Set[int] = set()
    saved_common_backs: Dict[int, str] = {}  # xref -> saved filename

    if common_back and not single_sided:
        print("Scanning for common backs...")
        xref_counts = scan_back_pages_for_common_backs(
            doc, skip_pages, min_dimension, single_sided
        )

        for xref, count in xref_counts.items():
            if count >= COMMON_BACK_THRESHOLD:
                common_backs.add(xref)
                print(f"  Detected common back: xref={xref} ({count} occurrences)")

        if common_backs:
            print(f"Found {len(common_backs)} common back image(s)")
        else:
            print("No common backs detected")

    # Track all fronts for pairing with backs
    # Key: (front_page, position_index) -> (image_bytes, ext, output_name)
    front_cards: Dict[Tuple[int, int], Tuple[bytes, str, str]] = {}

    # Track mismatched pages (front pages where backs had different card count)
    mismatched_fronts: Set[int] = set()

    # Pre-scan for layout mismatches (only in double-sided mode)
    if not single_sided:
        for page_num in range(0, total_pages - 1, 2):
            front_page_num = page_num
            back_page_num = page_num + 1
            front_page_display = front_page_num + 1
            back_page_display = back_page_num + 1

            if front_page_display in skip_pages or back_page_display in skip_pages:
                continue

            front_page = doc[front_page_num]
            back_page = doc[back_page_num]

            front_cards_list = get_card_images_from_page(doc, front_page, min_dimension)
            back_cards_list = get_card_images_from_page(doc, back_page, min_dimension)

            if len(front_cards_list) != len(back_cards_list) and len(back_cards_list) > 0:
                print(f"Warning: Layout mismatch - Page {front_page_display} has {len(front_cards_list)} cards, "
                      f"Page {back_page_display} has {len(back_cards_list)} cards")
                print(f"  Treating page {front_page_display} as single-sided (fronts only)")
                mismatched_fronts.add(front_page_display)

    # Process pages
    common_back_counter = 0

    for page_num in range(total_pages):
        page = doc[page_num]
        is_front_page = (page_num % 2 == 0) if not single_sided else True
        page_display = page_num + 1  # 1-indexed for display

        # Skip if in skip list
        if page_display in skip_pages:
            print(f"Page {page_display}: Skipped")
            continue

        cards = get_card_images_from_page(doc, page, min_dimension)

        if not cards:
            print(f"Page {page_display}: No cards found, skipping")
            continue

        # Detect or use grid
        detected_cols, detected_rows = detect_grid_size(cards)
        actual_count = len(cards)

        if grid_cols and grid_rows:
            expected_count = grid_cols * grid_rows
            if actual_count > expected_count:
                print(f"Page {page_display}: Found {actual_count} cards, expected max {expected_count} from grid")
        else:
            print(f"Page {page_display}: Detected {detected_cols}x{detected_rows} grid ({actual_count} cards)")

        # For short-edge flip, reverse the card order on back pages
        if short_edge_flip and not is_front_page:
            cards = list(reversed(cards))

        # Determine output subdirectory paths
        front_out = os.path.join(FRONT_DIR, output_subdir) if output_subdir else FRONT_DIR
        back_out = os.path.join(BACK_DIR, output_subdir) if output_subdir else BACK_DIR
        double_out = os.path.join(DOUBLE_SIDED_DIR, output_subdir) if output_subdir else DOUBLE_SIDED_DIR

        # Process each card
        for idx, card in enumerate(cards):
            position = idx + 1  # 1-indexed position

            # Build output name with optional prefix
            if filename_prefix:
                output_name = f"{filename_prefix}_{page_display}_{position}"
            else:
                output_name = f"{page_display}_{position}"

            if is_front_page or single_sided:
                # Save front image
                output_path = os.path.join(front_out, output_name)
                saved_path = save_image(card["image_bytes"], card["ext"], output_path)
                print(f"  Front: {os.path.basename(saved_path)}")

                # Store for back pairing (unless single-sided or mismatched)
                if not single_sided and page_display not in mismatched_fronts:
                    front_cards[(page_display, position)] = (
                        card["image_bytes"],
                        card["ext"],
                        output_name
                    )
            else:
                # Back page - check if it's a common back
                if card["xref"] in common_backs:
                    if card["xref"] not in saved_common_backs:
                        # Save common back once
                        common_back_counter += 1
                        common_back_name = f"back_{common_back_counter}"
                        output_path = os.path.join(back_out, common_back_name)
                        saved_path = save_image(card["image_bytes"], card["ext"], output_path)
                        saved_common_backs[card["xref"]] = os.path.basename(saved_path)
                        print(f"  Common back: {os.path.basename(saved_path)}")
                    else:
                        print(f"  Common back: (already saved as {saved_common_backs[card['xref']]})")
                else:
                    # Unique back - find matching front
                    front_page = page_display - 1  # Previous page is the front
                    front_key = (front_page, position)

                    if front_key in front_cards:
                        _, _, front_name = front_cards[front_key]
                        # Use front name for the back (for matching)
                        output_path = os.path.join(double_out, front_name)
                        saved_path = save_image(card["image_bytes"], card["ext"], output_path)
                        print(f"  Back:  {os.path.basename(saved_path)} (matches front {front_name})")
                    else:
                        # No matching front - save with back page naming
                        output_path = os.path.join(double_out, output_name)
                        saved_path = save_image(card["image_bytes"], card["ext"], output_path)
                        print(f"  Back:  {os.path.basename(saved_path)} (no matching front)")

    doc.close()

    # Summary
    front_path = os.path.join(FRONT_DIR, output_subdir) if output_subdir else FRONT_DIR
    back_path = os.path.join(BACK_DIR, output_subdir) if output_subdir else BACK_DIR
    double_path = os.path.join(DOUBLE_SIDED_DIR, output_subdir) if output_subdir else DOUBLE_SIDED_DIR

    front_count = len([f for f in os.listdir(front_path) if not f.startswith(".")]) if os.path.isdir(front_path) else 0
    back_count = len([f for f in os.listdir(back_path) if not f.startswith(".")]) if os.path.isdir(back_path) else 0
    double_count = len([f for f in os.listdir(double_path) if not f.startswith(".")]) if os.path.isdir(double_path) else 0

    print()
    print("Extraction complete!")
    print(f"  Fronts:       {front_count} images in {front_path}/")
    if back_count > 0:
        print(f"  Common backs: {back_count} images in {back_path}/")
    if double_count > 0:
        print(f"  Unique backs: {double_count} images in {double_path}/")


def find_pdf_pairs(folder_path: str) -> Dict[str, Dict[str, Optional[str]]]:
    """
    Find front/back PDF pairs in a folder.

    Detects pairs by filename patterns:
    - "Front" / "Back" suffix (e.g., CharactersFront.pdf / CharactersBack.pdf)
    - "_Cardbacks" suffix (e.g., LeaderCards.pdf / LeaderCards_Cardbacks.pdf)

    Returns:
        Dict mapping base_name -> {"front": path_or_None, "back": path_or_None, "subdir": relative_subdir}
    """
    pairs: Dict[str, Dict[str, Optional[str]]] = {}

    for root, _, files in os.walk(folder_path):
        pdf_files = [f for f in files if f.lower().endswith(".pdf")]
        rel_dir = os.path.relpath(root, folder_path)
        if rel_dir == ".":
            rel_dir = ""

        for pdf_file in pdf_files:
            full_path = os.path.join(root, pdf_file)
            base_name = pdf_file[:-4]  # Remove .pdf

            # Check for Front/Back pattern (case insensitive)
            front_match = re.match(r"(.+?)(Front)$", base_name, re.IGNORECASE)
            back_match = re.match(r"(.+?)(Back)$", base_name, re.IGNORECASE)
            cardbacks_match = re.match(r"(.+?)(_Cardbacks)$", base_name, re.IGNORECASE)

            if front_match:
                group_name = front_match.group(1)
                key = f"{rel_dir}/{group_name}" if rel_dir else group_name
                if key not in pairs:
                    pairs[key] = {"front": None, "back": None, "subdir": rel_dir}
                pairs[key]["front"] = full_path
            elif back_match:
                group_name = back_match.group(1)
                key = f"{rel_dir}/{group_name}" if rel_dir else group_name
                if key not in pairs:
                    pairs[key] = {"front": None, "back": None, "subdir": rel_dir}
                pairs[key]["back"] = full_path
            elif cardbacks_match:
                group_name = cardbacks_match.group(1)
                key = f"{rel_dir}/{group_name}" if rel_dir else group_name
                if key not in pairs:
                    pairs[key] = {"front": None, "back": None, "subdir": rel_dir}
                pairs[key]["back"] = full_path
            else:
                # Check if there's a matching _Cardbacks file
                cardbacks_name = f"{base_name}_Cardbacks.pdf"

                # Check case-insensitive
                cardbacks_exists = False
                for f in pdf_files:
                    if f.lower() == cardbacks_name.lower():
                        cardbacks_exists = True
                        break

                if cardbacks_exists:
                    # This is a front file with a _Cardbacks pair
                    key = f"{rel_dir}/{base_name}" if rel_dir else base_name
                    if key not in pairs:
                        pairs[key] = {"front": None, "back": None, "subdir": rel_dir}
                    pairs[key]["front"] = full_path
                else:
                    # Standalone PDF - treat as front-only
                    key = f"{rel_dir}/{base_name}" if rel_dir else base_name
                    if key not in pairs:
                        pairs[key] = {"front": full_path, "back": None, "subdir": rel_dir}

    return pairs


def process_folder(
    folder_path: str,
    grid: Optional[str] = None,
    short_edge_flip: bool = False,
    min_dimension: int = MIN_CARD_DIMENSION,
    skip_pages: Optional[Set[int]] = None,
    single_sided: bool = False,
    common_back: bool = True
) -> None:
    """
    Process a folder containing PDF files.

    Detects front/back PDF pairs and processes them appropriately.
    """
    print(f"Scanning folder: {folder_path}")
    pairs = find_pdf_pairs(folder_path)

    if not pairs:
        print("No PDF files found in folder")
        return

    print(f"Found {len(pairs)} PDF group(s):")
    for name, info in sorted(pairs.items()):
        front_status = "✓" if info["front"] else "✗"
        back_status = "✓" if info["back"] else "✗"
        print(f"  {name}: Front [{front_status}] Back [{back_status}]")

    print()

    for name, info in sorted(pairs.items()):
        front_pdf = info["front"]
        back_pdf = info["back"]
        subdir = info["subdir"]

        # Extract just the base name for prefix (remove path components)
        prefix = os.path.basename(name)

        if front_pdf and back_pdf:
            # Process as paired front/back PDFs
            print(f"\n{'='*60}")
            print(f"Processing pair: {name}")
            print(f"{'='*60}")

            # Process front PDF (single-sided mode for front file)
            print(f"\n--- Front PDF ---")
            process_pdf(
                front_pdf,
                grid=grid,
                short_edge_flip=short_edge_flip,
                min_dimension=min_dimension,
                skip_pages=skip_pages,
                single_sided=True,  # Front PDF is all fronts
                common_back=False,
                output_subdir=subdir,
                filename_prefix=prefix
            )

            # Process back PDF - skip if single-sided mode requested
            if not single_sided:
                print(f"\n--- Back PDF ---")
                process_back_pdf(
                    back_pdf,
                    grid=grid,
                    min_dimension=min_dimension,
                    skip_pages=skip_pages,
                    common_back=common_back,
                    output_subdir=subdir,
                    filename_prefix=prefix
                )
            else:
                print(f"\n--- Back PDF skipped (single-sided mode) ---")

        elif front_pdf:
            # Front-only PDF
            print(f"\n{'='*60}")
            print(f"Processing (front-only): {name}")
            print(f"{'='*60}")

            process_pdf(
                front_pdf,
                grid=grid,
                short_edge_flip=short_edge_flip,
                min_dimension=min_dimension,
                skip_pages=skip_pages,
                single_sided=True,
                common_back=False,
                output_subdir=subdir,
                filename_prefix=prefix
            )

        elif back_pdf:
            # Back-only PDF (unusual but handle it)
            print(f"\n{'='*60}")
            print(f"Processing (back-only): {name}")
            print(f"{'='*60}")

            if single_sided:
                # In single-sided mode, treat backs as fronts
                process_pdf(
                    back_pdf,
                    grid=grid,
                    short_edge_flip=short_edge_flip,
                    min_dimension=min_dimension,
                    skip_pages=skip_pages,
                    single_sided=True,
                    common_back=False,
                    output_subdir=subdir,
                    filename_prefix=prefix
                )
            else:
                process_back_pdf(
                    back_pdf,
                    grid=grid,
                    min_dimension=min_dimension,
                    skip_pages=skip_pages,
                    common_back=common_back,
                    output_subdir=subdir,
                    filename_prefix=prefix
                )

    print(f"\n{'='*60}")
    print("Folder processing complete!")
    print(f"{'='*60}")


def process_back_pdf(
    pdf_path: str,
    grid: Optional[str] = None,
    min_dimension: int = MIN_CARD_DIMENSION,
    skip_pages: Optional[Set[int]] = None,
    common_back: bool = True,
    output_subdir: str = "",
    filename_prefix: str = ""
) -> None:
    """
    Process a PDF containing only back images.

    All pages are treated as backs. Common back detection is applied.
    """
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    skip_pages = skip_pages or set()
    ensure_directories(output_subdir)

    doc = fitz.open(pdf_path)
    total_pages = len(doc)

    print(f"Processing back PDF: {pdf_path}")
    print(f"Total pages: {total_pages}")

    # Parse grid override if provided
    grid_cols, grid_rows = None, None
    if grid:
        try:
            parts = grid.lower().split("x")
            grid_cols, grid_rows = int(parts[0]), int(parts[1])
            print(f"Using grid override: {grid_cols}x{grid_rows}")
        except (ValueError, IndexError):
            print(f"Warning: Invalid grid format '{grid}', using auto-detection")

    # Common back detection
    common_backs: Set[int] = set()
    saved_common_backs: Dict[int, str] = {}

    if common_back:
        print("Scanning for common backs...")
        xref_counts: Counter = Counter()

        for page_num in range(total_pages):
            page_display = page_num + 1
            if page_display in skip_pages:
                continue

            page = doc[page_num]
            cards = get_card_images_from_page(doc, page, min_dimension)

            for card in cards:
                xref_counts[card["xref"]] += 1

        for xref, count in xref_counts.items():
            if count >= COMMON_BACK_THRESHOLD:
                common_backs.add(xref)
                print(f"  Detected common back: xref={xref} ({count} occurrences)")

        if common_backs:
            print(f"Found {len(common_backs)} common back image(s)")
        else:
            print("No common backs detected")

    # Determine output paths
    back_out = os.path.join(BACK_DIR, output_subdir) if output_subdir else BACK_DIR
    double_out = os.path.join(DOUBLE_SIDED_DIR, output_subdir) if output_subdir else DOUBLE_SIDED_DIR

    common_back_counter = 0

    for page_num in range(total_pages):
        page = doc[page_num]
        page_display = page_num + 1

        if page_display in skip_pages:
            print(f"Page {page_display}: Skipped")
            continue

        cards = get_card_images_from_page(doc, page, min_dimension)

        if not cards:
            print(f"Page {page_display}: No cards found, skipping")
            continue

        detected_cols, detected_rows = detect_grid_size(cards)
        actual_count = len(cards)
        print(f"Page {page_display}: Detected {detected_cols}x{detected_rows} grid ({actual_count} cards)")

        for idx, card in enumerate(cards):
            position = idx + 1

            if filename_prefix:
                output_name = f"{filename_prefix}_{page_display}_{position}"
            else:
                output_name = f"{page_display}_{position}"

            if card["xref"] in common_backs:
                if card["xref"] not in saved_common_backs:
                    common_back_counter += 1
                    common_back_name = f"back_{common_back_counter}"
                    if filename_prefix:
                        common_back_name = f"{filename_prefix}_{common_back_name}"
                    output_path = os.path.join(back_out, common_back_name)
                    saved_path = save_image(card["image_bytes"], card["ext"], output_path)
                    saved_common_backs[card["xref"]] = os.path.basename(saved_path)
                    print(f"  Common back: {os.path.basename(saved_path)}")
                else:
                    print(f"  Common back: (already saved as {saved_common_backs[card['xref']]})")
            else:
                # Unique back
                output_path = os.path.join(double_out, output_name)
                saved_path = save_image(card["image_bytes"], card["ext"], output_path)
                print(f"  Unique back: {os.path.basename(saved_path)}")

    doc.close()

    # Summary
    back_path = os.path.join(BACK_DIR, output_subdir) if output_subdir else BACK_DIR
    double_path = os.path.join(DOUBLE_SIDED_DIR, output_subdir) if output_subdir else DOUBLE_SIDED_DIR

    back_count = len([f for f in os.listdir(back_path) if not f.startswith(".")]) if os.path.isdir(back_path) else 0
    double_count = len([f for f in os.listdir(double_path) if not f.startswith(".")]) if os.path.isdir(double_path) else 0

    print()
    print("Back PDF extraction complete!")
    if back_count > 0:
        print(f"  Common backs: {back_count} images in {back_path}/")
    if double_count > 0:
        print(f"  Unique backs: {double_count} images in {double_path}/")


@click.command()
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--grid",
    default=None,
    help="Grid size override (e.g., '3x3', '2x4'). Auto-detected if not specified."
)
@click.option(
    "--short-edge-flip",
    is_flag=True,
    default=False,
    help="Use short-edge flip matching (reverses back card order)."
)
@click.option(
    "--min-size",
    default=MIN_CARD_DIMENSION,
    help=f"Minimum image dimension to be considered a card (default: {MIN_CARD_DIMENSION}px)."
)
@click.option(
    "--skip",
    default=None,
    help="Pages to skip (e.g., '1,3-5,7'). Comma-separated pages and ranges."
)
@click.option(
    "--single-sided",
    is_flag=True,
    default=False,
    help="Treat all pages as fronts (no front/back pairing)."
)
@click.option(
    "--no-common-back",
    is_flag=True,
    default=False,
    help="Disable common back detection (treat all backs as unique)."
)
def cli(
    path: str,
    grid: Optional[str],
    short_edge_flip: bool,
    min_size: int,
    skip: Optional[str],
    single_sided: bool,
    no_common_back: bool
):
    """
    Extract card images from a Print-and-Play PDF or folder of PDFs.

    PATH can be a single PDF file or a folder containing PDFs.

    For single PDFs, assumes alternating front/back pages (odd pages = fronts,
    even pages = backs). Card images are saved to game/front/, game/back/,
    and game/double_sided/ directories.

    For folders, detects front/back PDF pairs by filename patterns:
    - "Front"/"Back" suffix (e.g., CharactersFront.pdf / CharactersBack.pdf)
    - "_Cardbacks" suffix (e.g., LeaderCards.pdf / LeaderCards_Cardbacks.pdf)
    """
    skip_pages = parse_skip_pages(skip) if skip else None
    common_back = not no_common_back

    try:
        if os.path.isdir(path):
            process_folder(
                path,
                grid=grid,
                short_edge_flip=short_edge_flip,
                min_dimension=min_size,
                skip_pages=skip_pages,
                single_sided=single_sided,
                common_back=common_back
            )
        else:
            process_pdf(
                path,
                grid=grid,
                short_edge_flip=short_edge_flip,
                min_dimension=min_size,
                skip_pages=skip_pages,
                single_sided=single_sided,
                common_back=common_back
            )
    except Exception as e:
        print(f"Error: {e}")
        raise click.Abort()


if __name__ == "__main__":
    cli()
