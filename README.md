# Custom Card Games with Silhouette Cutting Machines

![Silhouette Card Maker Banner](hugo/static/images/scm_banner.png)

Ever wanted to make your own custom card game but without the hassle of a craft knife, a rotary cutter, or a paper guillotine? How about making your own proxies to playtest your favorite TCG?

You can do it all with the press of a button and a cutting machine! And I can show you how!

If this is your first time here, check out the [tutorial](https://alan-cha.github.io/silhouette-card-maker/tutorial/)! Please join our [Discord server](https://discord.gg/jhsKmAgbXc) too!

## Demo

Watch me cut **104 cards in 26 minutes** without breaking a sweat!

[![Proxying a MTG Commander Deck in 26 minutes](hugo/static/images/youtube_demo.png)](https://www.youtube.com/watch?v=RVHtqsRW8t8)

## Purpose

The purpose of this repo is to enable you to use a Silhouette cutting machine to create card games and proxies. Proxies are only intended to be used for casual play and playtesting.

Proxies should be easily identifiable as proxies. You may not use this repo to create counterfeit cards to deceive people or to play in sanctioned tournaments. You are only permitted to sell cards if you are the full privileged copyright holder.

## Contents

* [documentation](https://alan-cha.github.io/silhouette-card-maker)
* [tutorial](https://alan-cha.github.io/silhouette-card-maker/tutorial/)
* [supply list](https://alan-cha.github.io/silhouette-card-maker/tutorial/supplies/)
* [create_pdf.py](#create_pdfpy), a script for laying out your cards in a PDF
* [offset_pdf.py](#offset_pdfpy), a script for adding an offset to your PDF
* [clean_up.py](#clean_uppy), a script for clearing your card image directories
* [cutting_templates/](cutting_templates/), a directory containing Silhouette Studio cutting templates
* [calibration/](calibration/), a directory containing offset calibration sheets
* [examples/](examples/), a directory containing sample games
* [plugins/](plugins/), a directory containing scripts for streamlining card image acquisition

## Supported Sizes

The most common card sizes for games are:
* `standard`, for standard TCG cards
* `poker`
* `bridge`

Other notable card sizes include:
* `business`
* `euro_business`
* `credit`
* `photo`, for K-pop photocards

The table below shows all possible paper and card size combinations and the layout of the cards.

| Format | `letter` | `legal` | `tabloid` | `a4` | `a3` | `arch_b` |
|---|---|---|---|---|---|---|
| `standard` | 4x2 (8) | 5x2 (10) | 4x4 (16) | 4x2 (8) | 6x3 (18) | 6x3 (18) |
| `poker` | 4x2 (8) | 5x2 (10) | 4x4 (16) | 4x2 (8) | 4x4 (16) | 6x3 (18) |
| `bridge` | 4x2 (8) | 5x2 (10) | 4x4 (16) | 3x3 (9) | 6x3 (18) | 7x3 (21) |
| `american_mini` | 4x4 (16) | 7x3 (21) | 9x4 (36) | 4x4 (16) | 9x4 (36) | 10x4 (40) |
| `bridge_square` | 3x4 (12) | 5x3 (15) | 4x7 (28) | 3x4 (12) | 4x6 (24) | 4x7 (28) |
| `business` | 2x5 (10) | 2x6 (12) | 4x5 (20) | 2x5 (10) | 3x7 (21) | 3x8 (24) |
| `catan` | 3x3 (9) | 6x2 (12) | 7x3 (21) | 5x2 (10) | 7x3 (21) | 5x5 (25) |
| `credit` | 2x4 (8) | 2x6 (12) | 4x4 (16) | 2x5 (10) | 3x7 (21) | 3x7 (21) |
| `domino` | 5x2 (10) | 7x2 (14) | 5x4 (20) | 5x2 (10) | 8x3 (24) | 9x3 (27) |
| `domino_square` | 4x5 (20) | 7x4 (28) | 5x9 (45) | 4x5 (20) | 6x8 (48) | 6x9 (54) |
| `euro_business` | 3x3 (9) | 2x5 (10) | 3x7 (21) | 3x3 (9) | 3x7 (21) | 3x7 (21) |
| `euro_mini` | 4x3 (12) | 4x4 (16) | 9x3 (27) | 6x2 (12) | 8x4 (32) | 9x4 (36) |
| `japanese` | 4x2 (8) | 5x2 (10) | 4x4 (16) | 3x3 (9) | 6x3 (18) | 7x3 (21) |
| `jumbo` | 2x1 (2) | 2x2 (4) | 4x1 (4) | 3x1 (3) | 3x2 (6) | 3x3 (9) |
| `micro` | 7x4 (28) | 9x4 (36) | 7x9 (63) | 5x6 (30) | 11x6 (66) | 12x6 (72) |
| `mini` | 5x3 (15) | 7x3 (21) | 8x4 (32) | 4x4 (16) | 8x4 (32) | 9x4 (36) |
| `standard_double` | 2x2 (4) | 2x2 (4) | 4x2 (8) | 2x2 (4) | 3x3 (9) | 3x3 (9) |
| `tarot` | 2x2 (4) | 4x1 (4) | 5x2 (10) | 2x2 (4) | 5x2 (10) | 4x3 (12) |
| `70mm_square` | 3x2 (6) | 4x2 (8) | 5x3 (15) | 3x2 (6) | 5x3 (15) | 5x4 (20) |

The table below shows each card size, sorted by size.

| Card size | Inches | Millimeters | Ratio | Notes |
| --- | --- | --- | --- | --- |
| `jumbo` | **3.5 x 5.5** | 88.9 x 139.7 | 0.6364 |  |
| `standard_double` | 3.465 x 4.961 | **88 x 126** | 0.6984 | Magic: The Gathering oversized <ul><li>Planechase</li> <li>Archenemy</li> <li>Commander</li></ul> |
| `tarot` | **2.75 x 4.75** | 69.85 x 120.65 | 0.5789 |  |
| `poker` | **2.5 x 3.5** | 63.5 x 88.9 | 0.7143 |  |
| `bridge` | **2.25 x 3.5** | 57.15 x 88.9 | 0.6429 |  |
| `business` | **2 x 3.5** | 50.8 x 88.9 | 0.5714 | Business cards |
| `domino` | **1.75 x 3.5** | 44.45 x 88.9 | 0.5000 |  |
| `standard` | 2.48 x 3.465 | **63 x 88** | 0.7159 | AKA `euro_poker`<br>Most standard TCGs<ul><li>**Magic: The Gathering**</li><li>**Pokémon**</li><li>**Lorcana**</li><li>**One Piece**</li><li>**Riftbound**</li></ul> |
| `japanese` | 2.323 x 3.386 | **59 x 86** | 0.6860 |  |
| `credit` | **2.125 x 3.375** | 53.975 x 85.725 | 0.6296 | Credit cards <ul><li>CR80</li><li>ISO/IEC 7810</li></ul> |
| `euro_business` | 2.165 x 3.346 | **55 x 85** | 0.6471 | AKA `photo`<br>EU business cards<br>K-pop photocards |
| `catan` | 2.126 x 3.15 | **54 x 80** | 0.6750 |  |
| `70mm_square` | 2.756 x 2.756 | **70 x 70** | 1.0000 |  |
| `euro_mini` | 1.732 x 2.677 | **44 x 68** | 0.6471 | AKA `mini_euro` |
| `mini` | **1.75 x 2.5** | 44.45 x 63.5 | 0.7000 |  |
| `american_mini` | 1.614 x 2.48 | **41 x 63** | 0.6508 | AKA `mini_american` |
| `bridge_square` | **2.25 x 2.25** | 57.15 x 57.15 | 1.0000 |  |
| `domino_square` | **1.75 x 1.75** | 44.45 x 44.45 | 1.0000 |  |
| `micro` | **1.25 x 1.75** | 31.75 x 44.45 | 0.7143 |  |

The table below shows each paper size, sorted by size and standard.

| Paper size | Inches | Millimeters | Notes |
| --- | --- | --- | --- |
| `letter` | **8.5 x 11** | 215.9 x 279.4 | AKA `ansi_a` |
| `legal` | **8.5 x 14** | 215.9 x 355.6 |  |
| `tabloid` | **11 x 17** | 279.4 x 431.8 | AKA `ansi_b` |
| `a4` | 8.268 x 11.693 | **210 x 297** |  |
| `a3` | 11.693 x 16.535 | **297 x 420** |  |
| `arch_b` | **12 x 18** | 304.8 x 457.2 |  |

You can find all the cutting templates for Silhouette Studio in [`cutting_templates/`](cutting_templates/).

## Plugins

Plugins streamline the process for acquiring card images for various games.

The [Magic: The Gathering plugin](plugins/mtg/README.md) supports various decklist formats, including **Archidekt**, **CubeCobra**, **Deckstats**, **MPCFill**, **MTGA**, **MTGO**, **Moxfield**, and **Scryfall** formats.

The [Pokemon plugin](plugins/pokemon/README.md) supports **Limitless TCG** format.

The [Yu-Gi-Oh! plugin](plugins/yugioh/README.md) supports **YDK** and **YDKE** formats.

The [Altered plugin](plugins/altered/README.md) supports **Ajordat** format.

The [Arkham Horror: The Card Game plugin](plugins/arkham_horror_lcg/README.md) supports **ArkhamDB** format.

The [Ashes Reborn plugin](plugins/ashes_reborn/README.md) supports **Ashes** and **Ashes DB** formats.

The [Bushiroad plugin](plugins/bushiroad/README.md) supports **Bushiroad Deck Log** format for Cardfight Vanguard, Shadowverse: Evolve, Weiss Schwarz, Godzilla Card Game, and hololive.

The [Digimon plugin](plugins/digimon/README.md) supports **Digimoncard.app**, **Digimoncard.dev**, **Digimoncard.io**, **DigimonMeta**, **Tabletop Simulator**, and **Untap** formats.

The [Echoes of Astra plugin](plugins/echoes_of_astra/README.md) supports **AstraBuilder** format.

The [Elestrals plugin](plugins/elestrals/README.md) supports **Elestrals** format.

The [Final Fantasy plugin](plugins/final_fantasy/README.md) supports **OCTGN**, **Tabletop Simulator**, and **Untap** formats.

The [Flesh and Blood plugin](plugins/flesh_and_blood/README.md) supports **Fabrary** format.

The [Grand Archive plugin](plugins/grand_archive/README.md) supports **Omnideck** format.

The [Gundam plugin](plugins/gundam/README.md) supports **DeckPlanet**, **Egman Events**, **ExBurst**, and **Limitless TCG** formats.

The [KeyForge plugin](plugins/keyforge/README.md) supports **Master Vault** (including **Decks of KeyForge** links) and **Archon Arcana** formats.

The [Lord of the Rings: Living Card Game plugin](plugins/lotr_lcg/README.md) supports **RingsDB decklists**, **RingsDB fellowships**, and **RingsDB scenarios**, using user-supplied local back scans.

The [Lorcana plugin](plugins/lorcana/README.md) supports **Dreamborn** format.

The [Netrunner plugin](plugins/netrunner/README.md) supports **bbCode** and **Jinteki** formats.

The [One Piece plugin](plugins/one_piece/README.md) supports **Egman Events** and **OPTCG Simulator** formats.

The [Riftbound plugin](plugins/riftbound/README.md) supports **Piltover Archive**, **Pixelborn**, and **Tabletop Simulator** formats.

The [Sorcery: Contested Realm plugin](plugins/sorcery_contested_realm/README.md) supports **Curiosa** format.

The [Star Wars Unlimited plugin](plugins/star_wars_unlimited/README.md) supports **Melee**, **Picklist**, and **SWUDB** formats.

## create_pdf.py
`create_pdf.py` is a CLI tool that layouts your card images into a PDF with registration marks that can be cut out with the appropriate cutting template in [`cutting_templates/`](cutting_templates/).

![Example PDF](hugo/static/images/create_pdf.png)

### Basic Usage

Create a Python virtual environment.
```sh
python -m venv venv
```

Activate the Python virtual environment.

**Terminal (macOS/Linux):**
```sh
. venv/bin/activate
```

**PowerShell (Windows):**
```powershell
.\venv\Scripts\Activate.ps1
```

Download Python packages.
```sh
pip install -r requirements.txt
```

Put your front images in the `game/front/` folder.

Put your back image in the `game/back/` folder.

Run the script.

**Letter size paper:**
```sh
python create_pdf.py
```

**A4 size paper:**
```sh
python create_pdf.py --paper_size a4
```

Get your PDF at `game/output/game.pdf`.

**Note:** When printing the PDF with duplex printing (double-sided), use **long side flip** (flip on long edge) to ensure proper front and back alignment.

### Double-Sided Cards

To create double-sided cards, put front images in the `game/front/` folder and back images in the `game/double_sided/` folder. The filenames (and file extensions) must match for each pair.

### Corner Artifacts

If your card images have rounded corners, they they may be missing print bleed in the PDF. Because of the missing bleed, when the cards are cut, they may have a sliver of white on the corners.

![Extend corners](hugo/static/images/extend_corners.jpg)

The `--extend_corners` option can ameliorate this issue by filling the corner regions beyond the corner radius arc with pixels sampled from the arc edge. This generates bleed that matches the rounded corners.

```sh
python create_pdf.py --extend_corners 3.5mm
```

You may need to experiment with the corner radius value, but `3.5mm` is a good starting point for standard playing cards.

### Edge Artifacts

If your print bleed does not match your card image, then there may be an issue with your your card image.

This typically occurs when there is a thin border (often 1 pixel) on one or more sides of your card image. The border is difficult to see but because the print bleed is generated from the border, the print bleed will not match the card image.

```sh
python create_pdf.py --extend_edges 3
```

You may need to experiment with the corner radius value, but `3` (pixels) is a good starting point for standard playing cards.

## Extended Outer Bleed

The distance between cards in a layout is fixed at 1.25 mm. However, extending the outer bleed of the outer cards can reduce the possibility of white edges appearing on cut cards.

The `--extend_bleed` option extends the bleed on the outer edges of outer cards on **front pages** (odd-numbered pages), while `--extend_bleed_backs` extends the bleed on **back pages** (even-numbered pages).

```sh
python create_pdf.py --extend_bleed 2mm
python create_pdf.py --extend_bleed_backs 2mm
```

### Skip Cards

One solution for registration issues is to use a Post-It note to cover up cards near the registration marks.

However, if you would prefer to skip this manual step, you can skip the card near registration marks using the `--skip` option.

```sh
python create_pdf.py --skip 4
```

![Skip front](hugo/static/images/skip_front.png)

If you cut from the back, you might consider:

```sh
python create_pdf.py --skip 0
```

![Skip back](hugo/static/images/skip_back.png)

### Registration Marks

`create_pdf.py` generates the 3-corner registration mark pattern by default.

The release of the **Silhouette Cameo 5 Alpha** also introduced the new 4-corner registration mark pattern.

To generate a PDF with the new 4-corner registration mark pattern, use the `--registration` option.

```sh
python create_pdf.py --registration 4
```

However, Silhouette Cameo 5 Alpha users can still use the 3-corner registration mark pattern by setting machine to **Cameo 5** in Silhouette Studio.

To use a different registration mark orientation than the card layout, use the `--registration_orientation` option. This can be useful when printing a landscape card layout on paper loaded as portrait.

```sh
python create_pdf.py --registration_orientation portrait
```

### CLI Options

```
Usage: create_pdf.py [OPTIONS]

Options:
  --front_dir_path TEXT           The path to the directory containing the
                                  card fronts.  [default: game/front]
  --back_dir_path TEXT            The path to the directory containing one or
                                  more card backs.  [default: game/back]
  --double_sided_dir_path TEXT    The path to the directory containing card
                                  backs for double-sided cards.  [default:
                                  game/double_sided]
  --output_path TEXT              The desired path to the output PDF.
                                  [default: game/output/game.pdf]
  --output_images                 Create images instead of a PDF.
  --card_size [standard|poker|bridge|american_mini|bridge_square|business|catan|credit|domino|domino_square|euro_business|euro_mini|euro_poker|japanese|jumbo|micro|mini|mini_american|mini_euro|photo|standard_double|tarot|70mm_square]
                                  The desired card size.  [default: standard]
  --paper_size [letter|legal|tabloid|a4|a3|arch_b|ansi_a|ansi_b]
                                  The desired paper size.  [default: letter]
  --registration [3|4]            The desired registration pattern.  [default:
                                  3]
  --registration_orientation [portrait|landscape]
                                  Override the registration mark orientation
                                  without changing the card layout.
  --specialty [a4-commander|letter-commander]
                                  Use a specialty layout. Overrides card_size,
                                  paper_size, and registration settings.
  --only_fronts                   Only generate front pages.
  --fit [stretch|crop]            How to fit front and double-sided images to
                                  card size. 'stretch' allows distortion,
                                  'crop' preserves aspect ratio by center-
                                  cropping.  [default: stretch]
  --fit_backs [stretch|crop]      How to fit back images to card size.
                                  'stretch' allows distortion, 'crop'
                                  preserves aspect ratio by center-cropping.
  --crop TEXT                     Crop card edges of front and double-sided
                                  images (removes edges). Examples: 3mm,
                                  0.125in, 6.5.
  --crop_backs TEXT               Crop card edges of back images (removes
                                  edges). Examples: 3mm, 0.125in, 6.5.
  --extend_edges TEXT             Crop card edges and extend them for front
                                  and double-sided images. Examples: 3mm,
                                  0.125in.
  --extend_edges_backs TEXT       Crop card edges and extend them for back
                                  images only. Examples: 3mm, 0.125in.
  --extend_corners TEXT           Extend rounded corner regions to reduce
                                  corner artifacts for front and double-sided
                                  images. Examples: 3mm, 0.125in.
  --extend_corners_backs TEXT     Extend rounded corner regions to reduce
                                  corner artifacts for back images only.
                                  Examples: 3mm, 0.125in.
  --extend_bleed TEXT             Extend the outer bleed of outer cards on
                                  front pages (odd-numbered pages). Examples:
                                  3mm, 0.125in.
  --extend_bleed_backs TEXT       Extend the outer bleed of outer cards on
                                  back pages (even-numbered pages). Examples:
                                  3mm, 0.125in.
  --ppi INTEGER RANGE             Pixels per inch (PPI) when creating PDF.
                                  [default: 300; x>=0]
  --quality INTEGER RANGE         File compression quality.  [default: 100;
                                  0<=x<=100]
  --load_offset                   Apply saved offsets. See `offset_pdf.py` for
                                  more information.
  --skip INTEGER RANGE            Skip a card based on its index. Useful for
                                  registration issues. Examples: 0, 4.  [x>=0]
  --label TEXT                    Apply a custom label to each page.
  --show_outline                  Show a white outline for cutting paths.
  --borderless                    Use tighter inset to fit more cards per
                                  page.
  --version                       Show the version and exit.
  --help                          Show this message and exit.
```

### Examples

Create poker-sized cards with A4 sized paper.

```sh
python create_pdf.py --card_size poker --paper_size a4
```

Crop the borders of the front and double-sided images by 3 mm on all sides. This option is useful if your images already have print bleed like those from [MPCFill](https://mpcfill.com/).

```sh
python create_pdf.py --crop 3mm
```

Remove the [rounded corner artifacts](#corner-artifacts) and load the saved offset from [`offset_pdf.py`](#offset_pdfpy).

```sh
python create_pdf.py --extend_corners 3.5mm --load_offset
```

Produce a 600 pixels per inch (PPI) file with minimal compression.

```sh
python create_pdf.py --ppi 600 --quality 100
```

## offset_pdf.py

It's pivotal to ensure that your card fronts and backs are aligned. The front and back alignment is mainly determined by your printer, but it's not always possible to calibrate it.

`offset_pdf.py` is a CLI tool that adds an offset to every other page in a PDF. This offset can compensate for the natural offset of your printer, allowing you to have good front and back alignment. It also supports an angle offset to correct for rotational misalignment.

### Basic Usage

First, you must determine the offset by using the [calibration sheets](calibration/).

`<paper size>-calibration.pdf` has a front page and a back page.

![Calibration](hugo/static/images/calibration.png)

The front page is a simple grid of squares.

The back page is the same grid of squares, except each square has a slight offset. The following grid illustrates the applied offsets.

```
| (-2,  2) | (-1,  2) | ( 0,  2) | ( 1,  2) | ( 2,  2) |
--------------------------------------------------------
| (-2,  1) | (-1,  1) | ( 0,  1) | ( 1,  1) | ( 2,  1) |
--------------------------------------------------------
| (-2,  0) | (-1,  0) |  Center  | ( 1,  0) | ( 2,  0) |
--------------------------------------------------------
| (-2, -1) | (-1, -1) | ( 0, -1) | ( 1, -1) | ( 2, -1) |
--------------------------------------------------------
| (-2, -2) | (-1, -2) | ( 0, -2) | ( 1, -2) | ( 2, -2) |
```

To determine the required offset, print out `<paper size>-calibration.pdf` with the card stock you plan to use.

Shine a strong light on the front so you can see the shadows on the back. Determine which set of front and back squares are aligned. This set will provide your offset.

Create and start your virtual Python environment and install Python dependencies if you have not done so already. See [here](#basic-usage) for more information.

Run the script with your offset. This will move all your back sheets in the direction of your offset. A positive x value will move the back page to the right and a positive y value moves the back page up, relative to the back page's orientation.
```sh
python offset_pdf.py --x_offset -5 --y_offset 10
```

You can also apply an angle offset to correct for rotational misalignment. This will rotate all your back sheets clockwise in addition to offset.
```sh
python offset_pdf.py --x_offset -5 --y_offset 10 --angle 0.5
```

Get your offset PDF at `game/output/game_offset.pdf`.

### Large offset

If no square on your calibration sheet matches, then you'll need to create a new calibration sheet with an arbitrary offset. After determining the offset using the offset calibration sheet, you can add the two offsets to determine your true offset.

To create an offset calibration sheet, use the `--pdf_path` option, targeting the calibration sheet of your paper size. For example:

```sh
python offset_pdf.py --pdf_path calibration/letter-calibration.pdf --x_offset 30 --y_offset -10
```

This will produce `calibration/letter-calibration_offset.pdf`, which is the same as calibration sheet but with an offset of (30, -10).

Print this out and determine which set of front and back squares are aligned. If none are aligned, try generating another offset calibration sheet with a different arbitrary offset.

Let's say there is a set of a front and back squares and the offset is (5, 5). You can add the arbitrary offset with this offset to find the true offset.

```
(30, -10) + (5, 5) = (35, -5)
```

The true offset if (35, -5).

You can verify this is true by generating an offset calibration sheet using this offset.

```sh
python offset_pdf.py --pdf_path calibration/letter-calibration.pdf --x_offset 35 --y_offset -5
```

Print this out and the center set of front and back squares, (0, 0), should be aligned.

### Save Offset

You can save your x, y, and angle offset with the `--save` option. After saving your offset, it'll be automatically applied every time you run `offset_pdf.py`. You can override the loaded offset using `--x_offset`, `--y_offset`, and `--angle`.

```sh
python offset_pdf.py --x_offset -5 --y_offset 10 --angle 0.5 --save
```

Additionally, you can automatically apply a saved offset in [`create_pdf.py`](#create_pdfpy) by using the `--load_offset` option.

```sh
python create_pdf.py --load_offset
```

### CLI Options

```
Usage: offset_pdf.py [OPTIONS]

Options:
  --pdf_path TEXT         Path of the input PDF.
  --output_pdf_path TEXT  Desired path of the offset PDF.
  -x, --x_offset INTEGER  X-axis offset, relative to back page orientation
                          (positive = right, negative = left).
  -y, --y_offset INTEGER  Y-axis offset, relative to back page orientation
                          (positive = up, negative = down).
  -a, --angle FLOAT       Angle offset in degrees (positive = clockwise).
  -s, --save              Save offset values.
  --ppi INTEGER RANGE     Pixels per inch (PPI) when generating offset PDF.
                          [default: 300; x>=0]
  --help                  Show this message and exit.
```

## clean_up.py

`clean_up.py` deletes all images from `game/front/` and `game/double_sided/`, leaving the directories empty and ready for a new batch of cards.

### Usage

```sh
python clean_up.py
```

## Donate

If you enjoyed using Silhouette Card Maker, consider [donating](https://www.paypal.com/donate/?hosted_button_id=ZH2XCSLXERBW8) to help support the project. Thank you!
