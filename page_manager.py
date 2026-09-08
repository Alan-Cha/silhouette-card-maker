import math
from typing import List, NamedTuple, Tuple

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import matplotlib.lines as mlines
from PIL import Image
import io

import size_convert
from enums import Orientation, Registration

# Registration mark constraints (in mm)
MAX_REG_LENGTH_MM = 20.0
MAX_REG_THICKNESS_MM = 1.0
MAX_REG_INSET_MM = 86.36
MIN_REG_LENGTH_MM = 5.0
MIN_REG_THICKNESS_MM = 0.5
MIN_REG_INSET_MM = 10.0
REG_PADDING_MM = 1.5  # Extra clearance around registration marks

class CardLayout(NamedTuple):
    card_width_px: int
    card_height_px: int
    paper_width_px: int
    paper_height_px: int
    x_pos: List[int]
    y_pos: List[int]
    max_length_mm: float


def generate_reg_mark(
    paper_width: str,
    paper_height: str,
    inset: str,
    thickness: str,
    length: str,
    dpi: int,
    registration: Registration,
) -> Image.Image:
    """Generate a registration mark image for the given paper size.

    Args:
        paper_width: Paper width as a unit string (e.g. "11in").
        paper_height: Paper height as a unit string (e.g. "8.5in").
        inset: Distance from the paper edge to the registration marks.
        thickness: Line thickness for registration marks.
        length: Line length for registration marks.
        dpi: Resolution in dots per inch.
        registration: Registration pattern (THREE or FOUR).

    Returns:
        PIL Image (RGBA) with registration marks drawn on a transparent background.
    """
    paper_width_mm = size_convert.size_to_mm(paper_width)
    paper_height_mm = size_convert.size_to_mm(paper_height)
    inset_mm = size_convert.size_to_mm(inset)
    thickness_mm = size_convert.size_to_mm(thickness)
    thickness_pt = size_convert.size_to_pt(thickness)
    length_mm = size_convert.size_to_mm(length)

    # Constrain registration mark parameters within valid ranges.
    length_mm = max(MIN_REG_LENGTH_MM, min(length_mm, MAX_REG_LENGTH_MM))
    thickness_mm = max(MIN_REG_THICKNESS_MM, min(thickness_mm, MAX_REG_THICKNESS_MM))
    inset_mm = min(inset_mm, MAX_REG_INSET_MM)

    # Create figure sized to the paper dimensions
    fig = plt.figure(figsize=(paper_width_mm / 25.4, paper_height_mm / 25.4), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])  # Use full canvas
    ax.set_xlim(0, paper_width_mm)
    ax.set_ylim(0, paper_height_mm)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_facecolor('none')
    fig.patch.set_alpha(0.0)

    if registration == Registration.THREE:
        # Add filled black square (5x5mm at inset from left and top)
        square = Rectangle(
            (inset_mm, paper_height_mm - inset_mm - 5),
            5, 5,
            facecolor='black',
            edgecolor='black',
            linewidth=thickness_pt
        )
        ax.add_patch(square)
    else:  # Registration.FOUR
        # Top-left L-shape (horizontal line)
        x_start = inset_mm
        x_end = inset_mm + length_mm - (thickness_mm / 2)
        y_start = paper_height_mm - inset_mm
        y_end = paper_height_mm - inset_mm
        line = mlines.Line2D([x_start, x_end], [y_start, y_end], color='black', linewidth=thickness_pt)
        ax.add_line(line)

        # Top-left L-shape (vertical line)
        x_start = inset_mm
        x_end = inset_mm
        y_start = paper_height_mm - inset_mm
        y_end = paper_height_mm - inset_mm - length_mm + (thickness_mm / 2)
        line = mlines.Line2D([x_start, x_end], [y_start, y_end], color='black', linewidth=thickness_pt)
        ax.add_line(line)

    # Bottom-left L-shape (horizontal line)
    x_start = inset_mm
    x_end = inset_mm + length_mm - (thickness_mm / 2)
    y_start = inset_mm
    y_end = inset_mm
    line = mlines.Line2D([x_start, x_end], [y_start, y_end], color='black', linewidth=thickness_pt)
    ax.add_line(line)

    # Bottom-left L-shape (vertical line)
    x_start = inset_mm
    x_end = inset_mm
    y_start = inset_mm
    y_end = inset_mm + length_mm - (thickness_mm / 2)
    line = mlines.Line2D([x_start, x_end], [y_start, y_end], color='black', linewidth=thickness_pt)
    ax.add_line(line)

    # Top-right L-shape (horizontal line)
    x_start = paper_width_mm - inset_mm - length_mm + (thickness_mm / 2)
    x_end = paper_width_mm - inset_mm
    y_start = paper_height_mm - inset_mm
    y_end = paper_height_mm - inset_mm
    line = mlines.Line2D([x_start, x_end], [y_start, y_end], color='black', linewidth=thickness_pt)
    ax.add_line(line)

    # Top-right L-shape (vertical line)
    x_start = paper_width_mm - inset_mm
    x_end = paper_width_mm - inset_mm
    y_start = paper_height_mm - inset_mm
    y_end = paper_height_mm - inset_mm - length_mm + (thickness_mm / 2)
    line = mlines.Line2D([x_start, x_end], [y_start, y_end], color='black', linewidth=thickness_pt)
    ax.add_line(line)

    if registration == Registration.FOUR:
        # Bottom-right L-shape (horizontal line)
        x_start = paper_width_mm - inset_mm - length_mm + (thickness_mm / 2)
        x_end = paper_width_mm - inset_mm
        y_start = inset_mm
        y_end = inset_mm
        line = mlines.Line2D([x_start, x_end], [y_start, y_end], color='black', linewidth=thickness_pt)
        ax.add_line(line)

        # Bottom-right L-shape (vertical line)
        x_start = paper_width_mm - inset_mm
        x_end = paper_width_mm - inset_mm
        y_start = inset_mm
        y_end = inset_mm + length_mm - (thickness_mm / 2)
        line = mlines.Line2D([x_start, x_end], [y_start, y_end], color='black', linewidth=thickness_pt)
        ax.add_line(line)

    # Save output
    img_buf = io.BytesIO()
    plt.savefig(img_buf, format='png', transparent=True)
    img_buf.seek(0)
    img = Image.open(img_buf)
    plt.close(fig)  # Close the figure to free memory
    return img


"""
Card layout computation with strict registration-mark corner exclusion.

This module computes card positions on a page while respecting:
- paper orientation
- bleed spacing between cards
- Silhouette registration mark inset
- square corner exclusion zones where NOTHING may appear
  (neither cards nor bleed)

If no valid layout fits without intruding into corner zones,
layout generation FAILS explicitly.

────────────────────────────────────────────────────────────────────────────
TERMINOLOGY

paper edge
┌─────────────────────────────────────┐
│ inset                               │
│   ┌──────────────┐                  │
│   │ corner zone  │ ← corner_len     │
│   └──────────────┘                  │
│                                     │
│        usable area                  │
│   ┌─────────────────────────────┐   │
│   │   bleed | card | bleed      │   │
│   │   bleed | card | bleed      │   │
│   └─────────────────────────────┘   │
└─────────────────────────────────────┘

Definitions:
- inset: distance from paper edge to registration marks
- corner_len: how far registration marks extend inward
- corner zone: square (corner_len × corner_len) at each corner
- usable area: page minus margins
- grid: cards PLUS surrounding bleed (entire grid must avoid corner zones)
"""

# ─────────────────────────────────────────────────────────────────────────────
# 1. Normalize page size for orientation
# ─────────────────────────────────────────────────────────────────────────────

def normalize_page_size(
    orientation: Orientation,
    paper_width_px: int,
    paper_height_px: int,
) -> Tuple[int, int]:
    """
    layouts.json stores paper sizes as landscape (width > height).
    Portrait swaps width and height; card dimensions are never swapped.
    """
    if orientation == Orientation.PORTRAIT:
        return paper_height_px, paper_width_px
    return paper_width_px, paper_height_px


# ─────────────────────────────────────────────────────────────────────────────
# 2. Compute how many cards fit along one axis
# ─────────────────────────────────────────────────────────────────────────────

def compute_grid_fit(
    usable: int,
    card: int,
    bleed: int,
) -> int:
    """
    Compute how many cards fit along a single dimension.

    | bleed | card | bleed | card | bleed |
      ^---------------------------------^ usable
    
    But bleed can extend beyond the usable area. Only cards must be in the usable area.

    n cards require:
        n * card + (n - 1) * bleed

    so:
        n <= (usable + bleed) / (card + bleed)
    """
    if usable <= 0:
        return 0
    return max(0, math.floor((usable + bleed) / (card + bleed)))


# ─────────────────────────────────────────────────────────────────────────────
# 3. Select margins that avoid corner exclusion zones
# ─────────────────────────────────────────────────────────────────────────────

def select_best_margins(
    page_width: int,
    page_height: int,
    card_width: int,
    card_height: int,
    bleed: int,
    inset: int,
    corner_len: int,
) -> Tuple[int, int, int, int, int, int]:
    """
    Try margin strategies and select the one that:
    - keeps the ENTIRE grid (cards + bleed) out of corner zones
    - fits the maximum number of cards

    Returns:
        (cols, rows, margin_x, margin_y, usable_width, usable_height)

    Failure:
        Raises ValueError if no valid layout exists.

    Corner rule:
    A layout overlaps a corner zone if the grid intrudes within corner_len
    of the inset boundary on BOTH axes simultaneously.

    For each margin strategy, three candidate (cols, rows) counts are tried:
      1. (max_cols, max_rows) — maximum cards.
      2. (cols_clear, max_rows) — reduce cols until x gap clears the corner zone.
      3. (max_cols, rows_clear) — reduce rows until y gap clears the corner zone.
    Candidates 2 and 3 are symmetric: each shrinks one axis just enough to
    guarantee clearance on that axis, leaving the other axis at its maximum.
    """

    strategies = [
        (inset, inset),                    # minimal margins
        (inset + corner_len, inset),       # clear corners horizontally
        (inset, inset + corner_len),       # clear corners vertically
    ]

    best = None
    best_count = 0

    def record_if_valid(cols, rows, margin_x, margin_y, usable_width, usable_height):
        nonlocal best, best_count
        if cols <= 0 or rows <= 0:
            return
        grid_width = cols * card_width + (cols + 1) * bleed
        grid_height = rows * card_height + (rows + 1) * bleed
        gap_x = margin_x + (usable_width - grid_width) / 2 - inset
        gap_y = margin_y + (usable_height - grid_height) / 2 - inset
        if gap_x < corner_len and gap_y < corner_len:
            return
        count = cols * rows
        if count > best_count:
            best_count = count
            best = (cols, rows, margin_x, margin_y, usable_width, usable_height)

    for margin_x, margin_y in strategies:
        usable_width = page_width - 2 * margin_x
        usable_height = page_height - 2 * margin_y

        max_cols = compute_grid_fit(usable_width, card_width, bleed)
        max_rows = compute_grid_fit(usable_height, card_height, bleed)

        if max_cols == 0 or max_rows == 0:
            continue

        # Candidate 1: (max_cols, max_rows)
        record_if_valid(max_cols, max_rows, margin_x, margin_y, usable_width, usable_height)

        # Candidates 2 and 3: shrink one axis until that axis clears the corner zone.
        # Derived from gap >= corner_len:
        #   gap_x = margin_x + (usable_w - cols*(cw+b) - b)/2 - inset >= corner_len
        #   → cols <= (usable_w - b - 2*(corner_len - margin_x + inset)) / (cw+b)
        # (same formula for rows/y by symmetry)
        cols_clear = max(0, math.floor(
            (usable_width - bleed - 2 * (corner_len - margin_x + inset)) / (card_width + bleed)
        ))
        rows_clear = max(0, math.floor(
            (usable_height - bleed - 2 * (corner_len - margin_y + inset)) / (card_height + bleed)
        ))
        record_if_valid(cols_clear, max_rows, margin_x, margin_y, usable_width, usable_height)  # candidate 2
        record_if_valid(max_cols, rows_clear, margin_x, margin_y, usable_width, usable_height)  # candidate 3

    if best is None:
        raise ValueError(
            "No valid layout fits without intruding into corner exclusion zones."
        )

    return best


# ─────────────────────────────────────────────────────────────────────────────
# 4. Compute centered card positions
# ─────────────────────────────────────────────────────────────────────────────

def compute_card_positions(
    cols: int,
    rows: int,
    card_width: int,
    card_height: int,
    bleed: int,
    margin_x: int,
    margin_y: int,
    usable_width: int,
    usable_height: int,
) -> Tuple[List[int], List[int], int, int]:
    """
    Center the card grid within the usable area and return positions.
    """

    grid_width = cols * card_width + (cols + 1) * bleed
    grid_height = rows * card_height + (rows + 1) * bleed

    start_x = round(margin_x + (usable_width - grid_width) / 2 + bleed)
    start_y = round(margin_y + (usable_height - grid_height) / 2 + bleed)

    x_pos = [start_x + i * (card_width + bleed) for i in range(cols)]
    y_pos = [start_y + j * (card_height + bleed) for j in range(rows)]

    return x_pos, y_pos, start_x, start_y


def generate_layout(
    orientation: Orientation,
    card_width: str,
    card_height: str,
    paper_width: str,
    paper_height: str,
    inset: str,
    length: str,
    ppi: int,
):
    """
    Compute card positions on a page, accounting for margins, bleed,
    orientation, and strict registration mark corner exclusion zones.

    Raises:
        ValueError if no valid layout exists.
    """

    # Equivalent to double the bleed
    CARD_DISTANCE = "1.25mm"

    # Convert all dimensions to pixels
    page_width_px = size_convert.size_to_pixel(paper_width, ppi)
    page_height_px = size_convert.size_to_pixel(paper_height, ppi)
    card_width_px = size_convert.size_to_pixel(card_width, ppi)
    card_height_px = size_convert.size_to_pixel(card_height, ppi)
    card_distance_px = size_convert.size_to_pixel(CARD_DISTANCE, ppi)
    inset_px = size_convert.size_to_pixel(inset, ppi)
    length_px = size_convert.size_to_pixel(length, ppi)

    # Normalize orientation
    page_width_px, page_height_px = normalize_page_size(
        orientation, page_width_px, page_height_px
    )

    # Select margins and grid size (strict — no fallback)
    cols, rows, margin_x, margin_y, usable_w, usable_h = select_best_margins(
        page_width_px,
        page_height_px,
        card_width_px,
        card_height_px,
        card_distance_px,
        inset_px,
        length_px,
    )

    # Compute card positions
    x_pos, y_pos, start_x, start_y = compute_card_positions(
        cols,
        rows,
        card_width_px,
        card_height_px,
        card_distance_px,
        margin_x,
        margin_y,
        usable_w,
        usable_h,
    )

    # Maximum registration mark length that fits with a bleed safety buffer
    max_length_px = max(
        0,
        max(start_x - inset_px, start_y - inset_px) - card_distance_px
    )
    max_length_mm = round(max_length_px * 25.4 / ppi, 2)

    return CardLayout(
        card_width_px=card_width_px,
        card_height_px=card_height_px,
        paper_width_px=page_width_px,
        paper_height_px=page_height_px,
        x_pos=x_pos,
        y_pos=y_pos,
        max_length_mm=max_length_mm,
    )

