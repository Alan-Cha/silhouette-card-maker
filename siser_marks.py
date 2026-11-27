"""Siser Romeo & Juliet (Leonardo Design Studio) registration marks, SVG templates, and PDF calibration.

Integrates directly with silhouette-card-maker's exact card grid coordinates so that:
  1. Leonardo Design Studio SVG cut contours (single closed SVG 1.1 <path> per card,
     zero outer anchor boxes, zero strokes) match create_pdf.py's card layout to
     sub-millimeter precision.
  2. Running `create_pdf.py --registration siser` renders either:
       - Exact Leonardo Design Studio vector Page Marks (four pure corner L-brackets at
         6.000 mm centerline inset, 1.000 mm stroke thickness, 13.000 mm arm length from
         centerline — verified 1:1 against Leonardo's exported Printable PDF), OR
       - Calibrated registration marks + optional grid shift extracted verbatim from a
         local Leonardo Design Studio "Save PDF Artwork" export (stored in `siser_marks/`).
"""

from __future__ import annotations

import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import click
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np
from PIL import Image

import size_convert

REPO_ROOT = Path(__file__).resolve().parent
SISER_MARKS_DIR = REPO_ROOT / "siser_marks"
SISER_TEMPLATES_DIR = REPO_ROOT / "cutting_templates" / "siser"

MM_PER_PT = 25.4 / 72.0


def _marks_stem(paper_key: str, orientation_key: str) -> str:
    return f"{paper_key.lower()}_{orientation_key.lower()}"


def find_calibrated_marks(paper_key: Optional[str], orientation_key: Optional[str]) -> Tuple[Optional[Path], Optional[Dict[str, Any]]]:
    """Locate calibrated Leonardo marks PNG + metadata JSON if present for this paper/orientation."""
    if not paper_key or not SISER_MARKS_DIR.is_dir():
        return None, None
    orient = (orientation_key or "landscape").lower()
    candidates = [
        _marks_stem(paper_key, orient),
        paper_key.lower(),
    ]
    for stem in candidates:
        png_path = SISER_MARKS_DIR / f"{stem}_marks.png"
        meta_path = SISER_MARKS_DIR / f"{stem}_meta.json"
        if png_path.is_file():
            meta = None
            if meta_path.is_file():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                except Exception:
                    meta = None
            return png_path, meta
    return None, None


def get_siser_grid_shift_px(
    paper_key: Optional[str],
    orientation_key: Optional[str],
    base_ppi: int = 300,
) -> Tuple[int, int]:
    """Return calibrated (dx_px, dy_px) shift detected from Leonardo's Print-to-PDF."""
    _, meta = find_calibrated_marks(paper_key, orientation_key)
    if not meta:
        return 0, 0
    dx_mm = float(meta.get("grid_shift_dx_mm") or 0.0)
    dy_mm = float(meta.get("grid_shift_dy_mm") or 0.0)
    px_per_mm = base_ppi / 25.4
    return int(round(dx_mm * px_per_mm)), int(round(dy_mm * px_per_mm))


def generate_siser_reg_mark(
    paper_width_mm: float,
    paper_height_mm: float,
    dpi: int,
    paper_size_key: Optional[str] = None,
    orientation_key: Optional[str] = None,
) -> Image.Image:
    """Return a white RGB PIL image with Siser Romeo / Juliet Page Marks at exact page dimensions."""
    target_w = int(round(paper_width_mm / 25.4 * dpi))
    target_h = int(round(paper_height_mm / 25.4 * dpi))

    # 1. If calibrated Leonardo marks exist for this paper/orientation, stamp them verbatim!
    marks_png, _meta = find_calibrated_marks(paper_size_key, orientation_key)
    if marks_png is not None:
        with Image.open(marks_png) as overlay:
            rgba = overlay.convert("RGBA")
            # Auto-rotate overlay if saved portrait vs landscape
            if (rgba.width > rgba.height) != (target_w > target_h):
                rgba = rgba.rotate(-90, expand=True)
            if rgba.size != (target_w, target_h):
                rgba = rgba.resize((target_w, target_h), Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", (target_w, target_h), "white")
            canvas.paste(rgba, (0, 0), mask=rgba.getchannel("A"))
            return canvas

    # 2. Exact Leonardo Design Studio Page Marks (extracted directly from Leonardo's vector PDF).
    #    Verified vector rectangles in Leonardo's Printable PDF:
    #      - Centerline inset from all four paper edges: 6.000 mm
    #      - Stroke thickness: 1.000 mm (outer edge at 5.500 mm, inner edge at 6.500 mm)
    #      - Arm length from centerline: 13.000 mm (6.000 mm to 19.000 mm; total outer span 13.500 mm)
    #      - Four pure corner L-brackets (no bottom-left square).
    thickness_mm = 1.000
    half_t = thickness_mm / 2.0
    center_inset = 6.000
    arm_len = 13.000

    fig = plt.figure(figsize=(paper_width_mm / 25.4, paper_height_mm / 25.4), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, paper_width_mm)
    ax.set_ylim(0, paper_height_mm)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_facecolor("white")

    # Convert top-down mm rectangles (x0, y0, w, h) into matplotlib bottom-up patches
    rects_topdown = [
        # Top-left L
        (center_inset, center_inset - half_t, arm_len, thickness_mm),
        (center_inset - half_t, center_inset, thickness_mm, arm_len),
        # Top-right L
        (paper_width_mm - center_inset - arm_len, center_inset - half_t, arm_len, thickness_mm),
        (paper_width_mm - center_inset - half_t, center_inset, thickness_mm, arm_len),
        # Bottom-left L
        (center_inset, paper_height_mm - center_inset - half_t, arm_len, thickness_mm),
        (center_inset - half_t, paper_height_mm - center_inset - arm_len, thickness_mm, arm_len),
        # Bottom-right L
        (paper_width_mm - center_inset - arm_len, paper_height_mm - center_inset - half_t, arm_len, thickness_mm),
        (paper_width_mm - center_inset - half_t, paper_height_mm - center_inset - arm_len, thickness_mm, arm_len),
    ]
    for rx, ry_top, rw, rh in rects_topdown:
        ry_bot = paper_height_mm - (ry_top + rh)
        ax.add_patch(Rectangle((rx, ry_bot), rw, rh, facecolor="black", edgecolor="none"))

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, facecolor="white")
    plt.close(fig)
    buf.seek(0)
    img = Image.open(buf).convert("RGB")
    if img.size != (target_w, target_h):
        img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
    return img


def _compute_scm_slots_mm(
    paper_size: str,
    card_size: str = "standard",
    borderless: bool = False,
) -> Dict[str, Any]:
    """Compute exact card slot coordinates directly from silhouette-card-maker's layout engine."""
    import page_manager
    from utilities import load_layout_config

    cfg = load_layout_config()
    paper_def = cfg.paper_sizes[paper_size]
    if card_size not in cfg.card_sizes:
        raise KeyError(
            f"Card size '{card_size}' not found in layout config. "
            "Set SCM_EXTRA_LAYOUTS if using an scm-extras card size."
        )
    card_def = cfg.card_sizes[card_size]
    layout_variants = cfg.layouts[paper_size][card_size]
    layout_def = (
        layout_variants["borderless"]
        if (borderless and "borderless" in layout_variants)
        else layout_variants["default"]
    )
    default_reg = cfg.defaults.registration.borderless if borderless else cfg.defaults.registration.default

    eff_inset = (layout_def.registration.inset if layout_def.registration and layout_def.registration.inset else default_reg.inset)
    total_excl_mm = size_convert.size_to_mm(default_reg.length) + page_manager.REG_PADDING_MM

    computed = page_manager.generate_layout(
        orientation=layout_def.orientation,
        card_width=card_def.width,
        card_height=card_def.height,
        paper_width=paper_def.width,
        paper_height=paper_def.height,
        inset=eff_inset,
        length=f"{total_excl_mm}mm",
        ppi=cfg.ppi,
    )

    px_to_mm = 25.4 / cfg.ppi
    page_w_mm = computed.paper_width_px * px_to_mm
    page_h_mm = computed.paper_height_px * px_to_mm
    card_w_mm = size_convert.size_to_mm(card_def.width)
    card_h_mm = size_convert.size_to_mm(card_def.height)
    radius_str = card_def.radius or cfg.defaults.card_radius
    radius_mm = size_convert.size_to_mm(radius_str)

    slots: List[Dict[str, Any]] = []
    idx = 1
    for r, yp in enumerate(computed.y_pos):
        for c, xp in enumerate(computed.x_pos):
            slots.append(
                {
                    "index": idx,
                    "row": r,
                    "col": c,
                    "x_mm": round(xp * px_to_mm, 4),
                    "y_mm": round(yp * px_to_mm, 4),
                    "w_mm": round(card_w_mm, 4),
                    "h_mm": round(card_h_mm, 4),
                    "corner_radius_mm": round(radius_mm, 4),
                }
            )
            idx += 1

    return {
        "paper_size": paper_size,
        "card_size": card_size,
        "borderless": borderless,
        "orientation": layout_def.orientation.value,
        "page_w_mm": round(page_w_mm, 4),
        "page_h_mm": round(page_h_mm, 4),
        "cols": len(computed.x_pos),
        "rows": len(computed.y_pos),
        "slots": slots,
    }


def _rounded_rect_path_d(x: float, y: float, w: float, h: float, r: float) -> str:
    """Return a single closed SVG 1.1 <path> string (M/L/C/Z only) for a rounded rectangle."""
    r = max(0.0, min(r, w / 2.0, h / 2.0))
    # Exact cubic Bezier approximation for a 90-degree circular arc
    k = 0.5522847498 * r
    x0, y0 = x, y
    x1, y1 = x + w, y + h
    return (
        f"M {x0 + r:.4f} {y0:.4f} "
        f"L {x1 - r:.4f} {y0:.4f} "
        f"C {x1 - r + k:.4f} {y0:.4f} {x1:.4f} {y0 + r - k:.4f} {x1:.4f} {y0 + r:.4f} "
        f"L {x1:.4f} {y1 - r:.4f} "
        f"C {x1:.4f} {y1 - r + k:.4f} {x1 - r + k:.4f} {y1:.4f} {x1 - r:.4f} {y1:.4f} "
        f"L {x0 + r:.4f} {y1:.4f} "
        f"C {x0 + r - k:.4f} {y1:.4f} {x0:.4f} {y1 - r + k:.4f} {x0:.4f} {y1 - r:.4f} "
        f"L {x0:.4f} {y0 + r:.4f} "
        f"C {x0:.4f} {y0 + r - k:.4f} {x0 + r - k:.4f} {y0:.4f} {x0 + r:.4f} {y0:.4f} "
        f"Z"
    )


def build_leonardo_svg_for_layout(layout: Dict[str, Any], include_reference: bool = True) -> str:
    """Build a clean 96-DPI Leonardo-native SVG with ONLY exact single closed card <path>s.

    - Zero outer anchor/bounding boxes (Leonardo Page Marks anchor to paper corners).
    - Zero strokes (solid filled closed paths prevent hairline auto-trace fragmentation/double-cuts).
    - Explicit SVG 1.1 M/L/C/Z paths (no <rect rx/ry> or shorthand quirks).
    """
    px = 96.0 / 25.4
    w_mm = layout["page_w_mm"]
    h_mm = layout["page_h_mm"]
    w_px = w_mm * px
    h_px = h_mm * px
    slots = layout["slots"]
    gx0 = min(s["x_mm"] for s in slots)
    gy0 = min(s["y_mm"] for s in slots)
    gx1 = max(s["x_mm"] + s["w_mm"] for s in slots)
    gy1 = max(s["y_mm"] + s["h_mm"] for s in slots)
    gw = gx1 - gx0
    gh = gy1 - gy0

    variant_tag = "borderless" if layout["borderless"] else "default"
    role = "calibration" if include_reference else "cutonly"
    title = f"Siser {layout['paper_size'].upper()} {layout['card_size']} ({layout['cols']}x{layout['rows']} {variant_tag} {role})"
    fill_color = "#00A8E8" if include_reference else "#D9D9D9"
    group_id = "calibration-cards" if include_reference else "cut-contours"

    lines: List[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{w_mm:.3f}mm" height="{h_mm:.3f}mm" '
        f'viewBox="0 0 {w_px:.4f} {h_px:.4f}">',
        f"  <title>{title}</title>",
        f"  <!-- Exact silhouette-card-maker coordinates (96 DPI) | {layout['paper_size']} {layout['orientation']} | "
        f"Grid {gw:.3f}x{gh:.3f}mm ({gw/25.4:.4f}x{gh/25.4:.4f}in) | "
        f"{layout['card_size']} ({slots[0]['w_mm']}x{slots[0]['h_mm']}mm, r={slots[0]['corner_radius_mm']}mm) -->",
        f'  <g id="{group_id}">',
    ]

    for s in slots:
        d = _rounded_rect_path_d(
            s["x_mm"] * px,
            s["y_mm"] * px,
            s["w_mm"] * px,
            s["h_mm"] * px,
            s["corner_radius_mm"] * px,
        )
        lines.append(
            f'    <path id="card-{s["index"]}" d="{d}" fill="{fill_color}" stroke="none" />'
        )

    lines.extend(["  </g>", "</svg>", ""])
    return "\n".join(lines)


def generate_all_leonardo_svgs(
    output_dir: Path = SISER_TEMPLATES_DIR,
    card_size: str = "standard",
) -> List[Path]:
    """Generate exact-coordinate Leonardo Design Studio SVG templates for Letter & A4."""
    output_dir.mkdir(parents=True, exist_ok=True)
    targets = [
        ("letter", card_size, False, f"siser-letter-{card_size}"),
        ("a4", card_size, False, f"siser-a4-{card_size}"),
        ("a4", card_size, True, f"siser-a4-{card_size}-borderless"),
    ]
    written: List[Path] = []
    for paper, card, borderless, stem in targets:
        layout = _compute_scm_slots_mm(paper, card, borderless=borderless)
        for suffix, ref in (("-calibration.svg", True), ("-cutonly.svg", False)):
            out = output_dir / f"{stem}{suffix}"
            out.write_text(build_leonardo_svg_for_layout(layout, include_reference=ref), encoding="utf-8")
            written.append(out)
    return written


def extract_leonardo_pdf(
    pdf_path: Path,
    paper_size: str = "letter",
    card_size: str = "standard",
    borderless: bool = False,
    dpi: int = 600,
) -> Dict[str, Any]:
    """Extract Leonardo Design Studio's exact black registration marks + grid shift into siser_marks/."""
    try:
        import pymupdf as fitz
    except ImportError as exc:
        raise RuntimeError(
            "PDF calibration requires the optional 'pymupdf' package (pip install pymupdf)."
        ) from exc

    layout = _compute_scm_slots_mm(paper_size, card_size, borderless=borderless)
    orientation = layout["orientation"]
    slots = layout["slots"]
    nom_x0 = min(s["x_mm"] for s in slots)
    nom_y0 = min(s["y_mm"] for s in slots)
    nom_x1 = max(s["x_mm"] + s["w_mm"] for s in slots)
    nom_y1 = max(s["y_mm"] + s["h_mm"] for s in slots)

    doc = fitz.open(str(pdf_path))
    if doc.page_count < 1:
        doc.close()
        raise ValueError("Uploaded PDF has no pages.")

    page = doc[0]
    page_w_mm = page.rect.width * MM_PER_PT
    page_h_mm = page.rect.height * MM_PER_PT
    warnings: List[str] = []

    # Rotate 90 degrees if Leonardo exported portrait vs landscape
    if (
        abs(page_w_mm - layout["page_h_mm"]) < 3.5
        and abs(page_h_mm - layout["page_w_mm"]) < 3.5
    ):
        page.set_rotation((page.rotation + 90) % 360)
        page_w_mm = page.rect.width * MM_PER_PT
        page_h_mm = page.rect.height * MM_PER_PT
        warnings.append("Rotated Leonardo PDF 90 degrees to match card layout orientation.")

    if abs(page_w_mm - layout["page_w_mm"]) > 4.0 or abs(page_h_mm - layout["page_h_mm"]) > 4.0:
        warnings.append(
            f"PDF page size ({page_w_mm:.1f} x {page_h_mm:.1f} mm) differs from expected "
            f"{paper_size} ({layout['page_w_mm']:.1f} x {layout['page_h_mm']:.1f} mm)."
        )

    # Render at 600 DPI (works identically for both vector PDFs and Windows Microsoft Print to PDF!)
    scale = dpi / 72.0
    pix = page.get_pixmap(dpi=dpi, alpha=False)
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
    doc.close()

    r = arr[:, :, 0].astype(np.int16)
    g = arr[:, :, 1].astype(np.int16)
    b = arr[:, :, 2].astype(np.int16)

    # 1. Detect cyan calibration reference envelope (#00A8E8)
    cyan_mask = (b > 140) & (g > 100) & (r < 95) & ((b - r) > 85)
    cy_ys, cy_xs = np.where(cyan_mask)
    dx_mm, dy_mm = 0.0, 0.0
    cyan_found = False

    if cy_xs.size > 50:
        cyan_found = True
        det_x0_mm = float(cy_xs.min()) / scale * MM_PER_PT
        det_y0_mm = float(cy_ys.min()) / scale * MM_PER_PT
        det_x1_mm = float(cy_xs.max()) / scale * MM_PER_PT
        det_y1_mm = float(cy_ys.max()) / scale * MM_PER_PT
        det_cx = (det_x0_mm + det_x1_mm) / 2.0
        det_cy = (det_y0_mm + det_y1_mm) / 2.0
        nom_cx = (nom_x0 + nom_x1) / 2.0
        nom_cy = (nom_y0 + nom_y1) / 2.0
        dx_mm = round(det_cx - nom_cx, 3)
        dy_mm = round(det_cy - nom_cy, 3)
        excl_mm = (det_x0_mm + 1.5, det_y0_mm + 1.5, det_x1_mm - 1.5, det_y1_mm - 1.5)
    else:
        warnings.append(
            "Cyan calibration reference layer was not detected; kept centered card coordinates."
        )
        excl_mm = (nom_x0 + 1.5, nom_y0 + 1.5, nom_x1 - 1.5, nom_y1 - 1.5)

    # 2. Extract pure neutral black registration marks outside the card interior
    black_mask = (
        (r < 75)
        & (g < 75)
        & (b < 75)
        & (np.abs(r - g) < 25)
        & (np.abs(g - b) < 25)
    )
    px_per_mm = dpi / 25.4
    ix0 = max(0, int(round(excl_mm[0] * px_per_mm)))
    iy0 = max(0, int(round(excl_mm[1] * px_per_mm)))
    ix1 = min(pix.width, int(round(excl_mm[2] * px_per_mm)))
    iy1 = min(pix.height, int(round(excl_mm[3] * px_per_mm)))
    if ix1 > ix0 and iy1 > iy0:
        black_mask[iy0:iy1, ix0:ix1] = False

    black_pixels = int(black_mask.sum())
    if black_pixels < 30:
        raise ValueError(
            "No Siser registration marks detected outside the card grid. "
            "Ensure 'Print and Cut Job' is enabled in Leonardo Design Studio before exporting Print to PDF."
        )

    rgba = np.zeros((pix.height, pix.width, 4), dtype=np.uint8)
    rgba[black_mask, 3] = 255
    marks_img = Image.fromarray(rgba, mode="RGBA")

    SISER_MARKS_DIR.mkdir(parents=True, exist_ok=True)
    stem = _marks_stem(paper_size, orientation)
    marks_png_path = SISER_MARKS_DIR / f"{stem}_marks.png"
    marks_img.save(marks_png_path, format="PNG", optimize=True)

    meta = {
        "paper_size": paper_size,
        "orientation": orientation,
        "card_size": card_size,
        "borderless": borderless,
        "source_pdf": pdf_path.name,
        "extracted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dpi": dpi,
        "marks_png": marks_png_path.name,
        "black_pixels": black_pixels,
        "cyan_reference_detected": cyan_found,
        "grid_shift_dx_mm": dx_mm,
        "grid_shift_dy_mm": dy_mm,
        "warnings": warnings,
    }
    meta_path = SISER_MARKS_DIR / f"{stem}_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


@click.group()
def cli() -> None:
    """Siser Romeo & Juliet (Leonardo Design Studio) tools for silhouette-card-maker."""


@cli.command("generate-svgs")
@click.option("--card-size", default="standard", show_default=True, help="Card size key from layouts.json (or SCM_EXTRA_LAYOUTS).")
def cmd_generate_svgs(card_size: str) -> None:
    """Generate exact-coordinate Leonardo Design Studio SVG templates."""
    for p in generate_all_leonardo_svgs(card_size=card_size):
        click.echo(f"Wrote {p}")


@cli.command("calibrate")
@click.argument("leonardo_pdf", type=click.Path(exists=True, path_type=Path))
@click.option("--paper", default="letter", type=click.Choice(["letter", "a4"], case_sensitive=False))
@click.option("--card-size", default="standard", show_default=True)
@click.option("--borderless", is_flag=True, default=False)
def cmd_calibrate(leonardo_pdf: Path, paper: str, card_size: str, borderless: bool) -> None:
    """Extract Leonardo's exact registration marks from a Printable PDF export."""
    meta = extract_leonardo_pdf(leonardo_pdf, paper_size=paper.lower(), card_size=card_size, borderless=borderless)
    click.echo(f"Saved calibrated Siser marks: {SISER_MARKS_DIR / meta['marks_png']}")
    click.echo(f"Detected grid shift: dX={meta['grid_shift_dx_mm']} mm, dY={meta['grid_shift_dy_mm']} mm")
    for w in meta["warnings"]:
        click.echo(f"  WARNING: {w}")


@cli.command("status")
def cmd_status() -> None:
    """Show Siser Romeo & Juliet calibration status for Letter and A4."""
    for paper, orient in (("letter", "landscape"), ("a4", "landscape"), ("a4", "portrait")):
        png, meta = find_calibrated_marks(paper, orient)
        if png and meta:
            click.echo(
                f"{paper:6s} {orient:9s} | CALIBRATED ({meta.get('source_pdf')}) | "
                f"dX={meta.get('grid_shift_dx_mm', 0)} mm, dY={meta.get('grid_shift_dy_mm', 0)} mm"
            )
        else:
            click.echo(f"{paper:6s} {orient:9s} | BUILT-IN VECTOR (exact Leonardo Page Marks)")


if __name__ == "__main__":
    cli()
