import math
import ezdxf
import re
import size_convert
from ezdxf import units
from typing import List

# Write fixed timestamps and GUIDs so regenerated files are deterministic.
ezdxf.options.write_fixed_meta_data_for_testing = True

def add_circle(msp, x, y, width, height):
    """Add a circle as a DXF CIRCLE entity.

    For circular cards, width and height should be equal (the diameter).
    The circle is centered at (x + width/2, y + height/2) in DXF coordinates.
    """
    # Convert screen Y-down (origin top-left) to DXF Y-up (origin bottom-left)
    # Center the circle at the middle of the bounding box
    center_x = x + width / 2
    center_y = -y - height / 2
    radius = width / 2

    msp.add_circle((center_x, center_y), radius)


def add_rounded_rectangle(msp, x, y, width, height, radius):
    """Add a rounded rectangle as a single closed LWPOLYLINE with bulge factors.

    Uses LWPOLYLINE with bulge-encoded arcs for smooth line-to-arc joins.

    LINE+ARC entities were tried instead but rejected: SS renders a sharp
    corner where line meets arc instead of a smooth join. (LINE+ARC also
    merges multiple cards into one compound path, but Release Compound Path
    fixes that — the sharp corner is the actual blocker.)

    SS imports polyline paths at the coordinates as authored — confirmed by
    manually opening a DXF in SS with no automation involved, the path is
    never mirrored — but mirrors the image fill. flip_vertically() in
    dxf_to_studio3.py fixes the fill by mirroring the whole object, which
    mirrors the path too — a single combined flip, not two separate fixes.
    Harmless today since generate_dxf() only emits a single uniform corner
    radius (symmetric shapes); if per-corner radii are ever added, check
    against the printed card art which orientation is actually correct
    rather than assuming.

    Bulge factor for a 90° CCW arc = tan(22.5°) ≈ 0.4142.
    Positive bulge = CCW arc (left of travel direction).
    """
    # Convert screen Y-down (origin top-left) to DXF Y-up (origin bottom-left)
    y = -y - height

    BULGE = math.tan(math.radians(22.5))  # 90° CCW corner arc

    # Vertices: arc-start vertices carry the bulge value; edge-end vertices carry none.
    # Format: (x, y, bulge) — omitting bulge defaults to 0 (straight segment).
    points = [
        (x + width - radius, y,              BULGE),  # BR arc start
        (x + width,          y + radius),             # end of BR arc / bottom of right edge
        (x + width,          y + height - radius, BULGE),  # TR arc start
        (x + width - radius, y + height),             # end of TR arc / right of top edge
        (x + radius,         y + height,     BULGE),  # TL arc start
        (x,                  y + height - radius),    # end of TL arc / top of left edge
        (x,                  y + radius,     BULGE),  # BL arc start
        (x + radius,         y),                      # end of BL arc / left of bottom edge
    ]
    msp.add_polyline2d(points, format="xyb", close=True)


# Create new DXF document
def generate_dxf(card_width: str, card_height: str, card_radius: str, x_pos: List[int], y_pos: List[int], ppi:int, output_path:str, shape:str = "rectangle"):
    doc = ezdxf.new(dxfversion='R2010')
    float_pattern = r"(?:\d+\.\d*|\.\d+|\d+)"  # matches 1.0, .5, or 2
    # Match in or mm (default=mm)
    in_width = re.fullmatch(rf"({float_pattern})in", card_width)
    if in_width:
        doc.units = units.IN
        width = size_convert.size_to_in(card_width)
        height = size_convert.size_to_in(card_height)
        radius = size_convert.size_to_in(card_radius)
    else:
        doc.units = units.MM
        width = size_convert.size_to_mm(card_width)
        height = size_convert.size_to_mm(card_height)
        radius = size_convert.size_to_mm(card_radius)

    msp = doc.modelspace()

    for x in range(len(x_pos)):
        for y in range(len(y_pos)):
            if doc.units == units.IN:
                pos_x = x_pos[x] / ppi
                pos_y = y_pos[y] / ppi
            else:
                pos_x = x_pos[x] * 25.4 / ppi
                pos_y = y_pos[y] * 25.4 / ppi

            if shape == "circle":
                add_circle(msp, pos_x, pos_y, width, height)
            else:
                add_rounded_rectangle(msp, pos_x, pos_y, width, height, radius)


    # Strip non-deterministic metadata so regenerated files don't produce
    # spurious diffs when the geometry hasn't changed.
    for var in (
        "$TDCREATE", "$TDUCREATE",
        "$TDUPDATE", "$TDUUPDATE",
        "$FINGERPRINTGUID", "$VERSIONGUID",
    ):
        if var in doc.header:
            del doc.header[var]

    # Save DXF
    doc.saveas(output_path)