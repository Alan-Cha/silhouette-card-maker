# AGENTS.md

This file provides context for AI coding assistants working on this project.

## Project Overview

**Silhouette Card Maker** is a collection of tools and cutting templates for utilizing Silhouette cutting machines to cut cards. Users can create DIY card games or proxies for various trading card games (TCGs).

The project consists of:
- Python scripts for PDF generation and offset calibration
- Silhouette Studio cutting templates
- Plugins for fetching card images from various TCG databases
- A Hugo documentation site

## Directory Structure

```
silhouette-card-maker/
├── create_pdf.py          # Main script for laying out cards in a PDF
├── offset_pdf.py          # Script for adding offset to PDFs (printer calibration)
├── requirements.txt       # Python dependencies
├── cutting_templates/     # Silhouette Studio cutting templates (.studio3 files)
├── calibration/           # Offset calibration sheets for printer alignment
├── examples/              # Sample card games
├── game/                  # Working directory for card images
│   ├── front/             # Card front images
│   ├── back/              # Card back images
│   ├── double_sided/      # Back images for double-sided cards
│   ├── decklist/          # Decklist files for plugins
│   └── output/            # Generated PDFs
├── plugins/               # Card image acquisition scripts
│   ├── mtg/               # Magic: The Gathering
│   ├── yugioh/            # Yu-Gi-Oh!
│   ├── pokemon/           # Pokemon TCG
│   ├── lorcana/           # Disney Lorcana
│   ├── digimon/           # Digimon
│   ├── one_piece/         # One Piece TCG
│   ├── flesh_and_blood/   # Flesh and Blood
│   ├── star_wars_unlimited/ # Star Wars: Unlimited
│   └── ...                # Other TCG plugins
├── hugo/                  # Hugo documentation site
│   ├── content/           # Markdown content
│   ├── static/            # Static assets (images)
│   └── themes/hextra/     # Hugo theme (submodule)
└── README.md              # Main documentation
```

## Documentation Sync Requirement

**IMPORTANT:** The README.md and Hugo site documentation are closely aligned and must be kept in sync.

When documentation changes are made, similar changes need to be made in both locations:

| README.md Section | Hugo Content Location |
|-------------------|----------------------|
| Root README.md | `hugo/content/_index.md` |
| `create_pdf.py` docs | `hugo/content/docs/create.md` |
| `offset_pdf.py` docs | `hugo/content/docs/offset.md` |
| `plugins/<game>/README.md` | `hugo/content/plugins/<game>.md` |

The Hugo site is deployed to: https://alan-cha.github.io/silhouette-card-maker

## Script Reference

### User-facing scripts

Run by end users as part of the normal card-making workflow.

| Script | Purpose |
|--------|---------|
| `create_pdf.py` | Lay out card images into a print-ready PDF with registration marks |
| `offset_pdf.py` | Add x/y/angle offset to a PDF to compensate for printer front/back misalignment |
| `clean_up.py` | Delete all images from `game/front/` and `game/double_sided/` to start fresh |

### Developer/maintainer tools

Run by maintainers to regenerate project artifacts. Not needed for normal card-making use.

| Script | Purpose |
|--------|---------|
| `generate_calibration.py` | Generate calibration PDFs for all paper sizes |
| `generate_dxf.py` | Generate DXF cutting templates from `assets/layouts.json` |
| `dxf_to_studio3.py` | Convert DXF files to Silhouette Studio `.studio3` format; subcommands: `convert` (single file), `batch` (all DXFs), `calibrate` (record UI coordinates) |
| `generate_readme_tables.py` | Regenerate the card/paper size tables in `README.md` and Hugo docs |

### Internal modules

Imported by other scripts. Not intended to be run directly.

| Module | Purpose |
|--------|---------|
| `utilities.py` | Shared data loading: `LayoutConfig`, `load_layout_config`, `template_name`, etc. |
| `enums.py` | Shared enums: `Orientation` |
| `size_convert.py` | Unit conversion utilities (pixels, mm, inches) |
| `page_manager.py` | Card layout and page geometry calculations |
| `dxf_manager.py` | DXF file generation utilities |

### Key Script Details

#### create_pdf.py
Creates PDFs with card layouts and registration marks for cutting. Supports multiple card sizes (standard, japanese, poker, bridge, tarot, etc.) and paper sizes (letter, legal, tabloid, a4, a3, arch_b).

Key options:
- `--card_size` / `--paper_size`: Card and paper dimensions
- `--extend_corners`: Fix artifacts from rounded corner images
- `--crop`: Crop existing print bleed from images
- `--load_offset`: Apply saved printer offset
- `--skip`: Skip cards near registration marks

#### offset_pdf.py
Adds offset to every other page in a PDF to compensate for printer front/back misalignment. Supports x/y offset and angle rotation.

Key options:
- `--x_offset` / `--y_offset`: Pixel offset values
- `--angle`: Rotational offset in degrees
- `--save`: Persist offset values for future use

## Plugin Structure

Each plugin follows a similar pattern:

```
plugins/<game>/
├── README.md           # Plugin documentation
├── fetch.py            # Main entry point CLI
├── deck_formats.py     # Decklist format parsers
└── <api>.py            # API client for card database
```

Plugins read decklists and download card images to `game/front/` (and `game/double_sided/` for double-faced cards).

Supported games include: Altered, Ashes Reborn, Bushiroad, Digimon, Echoes of Astra, Elestrals, Final Fantasy, Flesh and Blood, Grand Archive, Gundam, KeyForge, Lorcana, MTG, Netrunner, One Piece, Pokemon, Riftbound, Sorcery: Contested Realm, Star Wars: Unlimited, and Yu-Gi-Oh!

## Development Setup

```sh
# Create virtual environment
python -m venv venv

# Activate (macOS/Linux)
. venv/bin/activate

# Activate (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

## Hugo Site Development

The documentation site uses Hugo with the Hextra theme.

```sh
cd hugo
hugo server
```

The theme is included as a git submodule in `hugo/themes/hextra/`.

## Supported Card Sizes

| Size | Dimensions | Common Games |
|------|-----------|--------------|
| `standard` | 63x88mm | MTG, Pokemon, Lorcana, One Piece, Digimon, Star Wars: Unlimited |
| `standard_double` | 126x88mm | MTG oversized (Planechase, Archenemy, Commander) |
| `japanese` | 59x86mm | Yu-Gi-Oh! |
| `poker` | 2.5x3.5in | Standard playing cards |
| `bridge` | 2.25x3.5in | Bridge cards |
| `tarot` | 2.75x4.75in | Tarot cards |

## Code Style Notes

- Python scripts use Click for CLI argument parsing
- Card images are processed with Pillow (PIL)
- PDFs are generated using reportlab
- Hugo content uses Hextra shortcodes (e.g., `{{< youtube >}}`, `{{% ref %}}`)

## Testing Workflow

1. Place test card images in `game/front/`
2. Run `python create_pdf.py` with desired options
3. Check output at `game/output/game.pdf`
4. For double-sided, also run `python offset_pdf.py` if calibration is needed
