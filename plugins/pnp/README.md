# PnP (Print and Play) Plugin

This plugin extracts card images from Print-and-Play game PDFs and organizes them into the appropriate directories for processing with `create_pdf.py`.

## Requirements

- PyMuPDF (`pip install pymupdf`)

## Basic Usage

```sh
# Single PDF file
python plugins/pnp/extract.py path/to/game.pdf

# Folder of PDFs
python plugins/pnp/extract.py path/to/pnp_folder/
```

This will extract card images and place them in:
- `game/front/` - Front card images
- `game/back/` - Common back images (shared across multiple cards)
- `game/double_sided/` - Unique back images (named to match fronts)

## CLI Options

```
Usage: extract.py [OPTIONS] PATH

  Extract card images from a Print-and-Play PDF or folder of PDFs.

  PATH can be a single PDF file or a folder containing PDFs.

Options:
  --grid TEXT          Grid size override (e.g., '3x3', '2x4'). Auto-detected
                       if not specified.
  --short-edge-flip    Use short-edge flip matching (reverses back card order).
  --min-size INTEGER   Minimum image dimension to be considered a card
                       (default: 200px).
  --skip TEXT          Pages to skip (e.g., '1,3-5,7'). Comma-separated pages
                       and ranges.
  --single-sided       Treat all pages as fronts (no front/back pairing).
  --no-common-back     Disable common back detection (treat all backs as unique).
  --help               Show this message and exit.
```

## How It Works

```
IDEAL PDF STRUCTURE (Alternating Pages)
========================================
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ Page 1   │  │ Page 2   │  │ Page 3   │  │ Page 4   │
│ FRONTS   │  │ BACKS    │  │ FRONTS   │  │ BACKS    │
│┌──┬──┬──┐│  │┌──┬──┬──┐│  │┌──┬──┬──┐│  │┌──┬──┬──┐│
││1 │2 │3 ││  ││3 │2 │1 ││  ││7 │8 │9 ││  ││9 │8 │7 ││
│├──┼──┼──┤│  │├──┼──┼──┤│  │├──┼──┼──┤│  │├──┼──┼──┤│
││4 │5 │6 ││  ││6 │5 │4 ││  ││10│11│12││  ││12│11│10││
│└──┴──┴──┘│  │└──┴──┴──┘│  │└──┴──┴──┘│  │└──┴──┴──┘│
└─────────-┘  └─────────-┘  └─────────-┘  └─────────-┘
```

1. **Image Extraction**: Extracts all images from the PDF using PyMuPDF
2. **Filtering**: Removes small images (logos, icons) based on minimum size threshold
3. **Grid Detection**: Auto-detects the card grid layout per page (e.g., 2x3, 3x3)
4. **Position Sorting**: Sorts cards top-to-bottom, left-to-right
5. **Front/Back Pairing**: Assumes odd pages are fronts, even pages are backs
6. **Common Back Detection**: Identifies shared backs to avoid duplicate files
7. **Naming**: Files are named `{page}_{position}.{ext}` (e.g., `1_3.png`)

## Common Back Detection

When the same back image appears 10 or more times across back pages, it's considered a "common back" and saved once to `game/back/` instead of duplicating it for each card.

```
COMMON BACK DETECTION
=====================
Back pages scanned → Count image occurrences
  ┌────────────────────────────────────┐
  │ xref=181: 21 times → COMMON BACK   │ → game/back/back_1.png
  │ xref=186:  5 times → COMMON BACK   │ → game/back/back_2.png
  │ xref=004:  1 time  → UNIQUE        │ → game/double_sided/
  └────────────────────────────────────┘
```

This significantly reduces file count for games where most cards share the same back design.

## Folder Mode (Front/Back PDF Pairs)

When given a folder path, the plugin automatically detects front/back PDF pairs by filename:

```
FOLDER MODE (Front/Back PDF Pairs)
==================================
Chain Mail PNP/
├── CharactersFront.pdf  ─┐
├── CharactersBack.pdf   ─┴→ Paired
├── ResourcesFront.pdf   ─┐
├── ResourcesBack.pdf    ─┴→ Paired
└── RulesInside.pdf      ─→ Skipped (no cards)
```

### Supported Naming Patterns

- **Front/Back suffix**: `CharactersFront.pdf` / `CharactersBack.pdf`
- **_Cardbacks suffix**: `LeaderCards.pdf` / `LeaderCards_Cardbacks.pdf`

### Subfolder Preservation

Nested folder structures are preserved in the output:

```
Input:                          Output:
2R1B/                          game/front/2R1B/Team Cards/
├── Team Cards/                game/back/2R1B/Team Cards/
│   ├── BlueTeamFront.pdf     game/double_sided/2R1B/Team Cards/
│   └── BlueTeamBack.pdf
```

### Output Naming for Folders

Files from folder mode are named: `{pdf_basename}_{page}_{position}.{ext}`

Example: `Characters_1_3.png` (from CharactersFront.pdf, page 1, position 3)

## Layout Mismatch Handling

When a front page and its corresponding back page have different card counts, the plugin treats the front page as single-sided:

```
LAYOUT MISMATCH DETECTION
=========================
Page 5 (front): 6 cards
Page 6 (back): 1 card  ← MISMATCH

Result: Page 5 treated as single-sided (fronts only)
        Page 6 back not paired
```

## Examples

### Basic extraction
```sh
python plugins/pnp/extract.py game/output/my_game.pdf
```

### With grid override
If auto-detection fails, specify the grid manually:
```sh
python plugins/pnp/extract.py game/output/my_game.pdf --grid 3x3
```

### Short-edge flip
For PDFs designed for short-edge flip printing:
```sh
python plugins/pnp/extract.py game/output/my_game.pdf --short-edge-flip
```

### Adjust minimum card size
If small cards aren't being detected:
```sh
python plugins/pnp/extract.py game/output/my_game.pdf --min-size 100
```

### Skip instruction pages
Skip specific pages (like cover pages or instructions):
```sh
python plugins/pnp/extract.py game/output/my_game.pdf --skip 1,11-20
```

### Single-sided extraction
If your PDF has all fronts (no backs to pair):
```sh
python plugins/pnp/extract.py game/output/my_game.pdf --single-sided
```

### Disable common back detection
If backs are incorrectly grouped as common:
```sh
python plugins/pnp/extract.py game/output/my_game.pdf --no-common-back
```

### Process a folder of PDFs
```sh
python plugins/pnp/extract.py "path/to/Chain Mail PNP/"
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Cards not detected | Lower `--min-size` (default: 200) |
| Too many small images extracted | Increase `--min-size` |
| Backs in wrong order | Try `--short-edge-flip` |
| Backs incorrectly grouped | Use `--no-common-back` |
| Instruction pages extracted | Use `--skip` to exclude them |
| Wrong grid detected | Override with `--grid 3x3` |
| Front/back count mismatch | Use `--single-sided` or fix manually |

## Output Naming Convention

### Single PDF Mode
- Front images: `{page}_{position}.{ext}` (e.g., `1_1.png`, `1_2.png`)
- Common backs: `back_{n}.{ext}` (e.g., `back_1.png`)
- Unique backs: Same name as matching front (e.g., `1_1.png` in `double_sided/`)

### Folder Mode
- Front images: `{basename}_{page}_{position}.{ext}` (e.g., `Characters_1_1.png`)
- Common backs: `{basename}_back_{n}.{ext}` (e.g., `Characters_back_1.png`)
- Unique backs: `{basename}_{page}_{position}.{ext}` (e.g., `Characters_1_1.png`)

Position is 1-indexed, ordered top-to-bottom, left-to-right.

## Limitations

- Assumes alternating front/back pages for single PDFs (page 1 = fronts, page 2 = backs, etc.)
- May not work with PDFs that have non-standard layouts
- Common back threshold is fixed at 10+ occurrences
- Does not currently sort by card size/aspect ratio
