# Siser Romeo & Juliet (Leonardo Design Studio) Templates

These 96-DPI SVG cutting templates match `silhouette-card-maker`'s exact card coordinates for **Siser Romeo** and **Siser Juliet** cutters using **Leonardo Design Studio**.

## Files
- `*-cutonly.svg`: Clean cut-contour templates containing **only** one closed SVG 1.1 `<path>` (`M/L/C/Z`, `stroke="none"`) per card slot — no outer anchor boxes, no strokes, and no interior reference lines.
- `*-calibration.svg`: Identical card paths filled in cyan (`#00A8E8`) for optional one-time PDF alignment calibration via `python siser_marks.py calibrate <leonardo.pdf> --paper letter|a4`.

## Usage in Leonardo Design Studio
1. Import the `*-cutonly.svg` file as **Editable Artwork / Cut Only** (do **not** use the Print & Cut bitmap auto-tracer, which degrades straight vector lines).
2. Enable **Print and Cut Job**, **Small Page Margins**, and **Page Marks** for your matching paper size (US Letter or A4) and click **Recenter**.
3. Save the Leonardo project (`.lds`) as your reusable cut template.
4. Generate your card sheet with `--registration siser` (e.g. `python create_pdf.py --paper_size letter --card_size standard --registration siser`), print at **Actual Size / 100%** with **Borderless Printing OFF** (borderless mode silently scales/crops pages on many printers), load on the cutting mat, and cut from your saved `.lds` template.
5. No calibration step is required for centered Page Marks layouts — `silhouette-card-maker` draws Leonardo's exact vector Page Marks natively (`6.000 mm` centerline inset, `1.000 mm` stroke, `13.000 mm` arms).

## Regenerating Templates
```bash
python siser_marks.py generate-svgs                                # standard (Letter + A4)
SCM_EXTRA_LAYOUTS=/path/to/layouts_extra.json python siser_marks.py generate-svgs --card-size standard_mtg
```
