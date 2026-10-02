# Star Trek CCG Plugin

This plugin reads a Star Trek CCG Second Edition decklist, fetches the card images from [Webula](https://github.com/iftheshoefritz/webula), which mirrors the card data and images of the official LackeyCCG Star Trek 2E plugin, and puts the card images into the proper `game/` directories.

This plugin supports the `trekcc` and `lackey` decklist formats. To learn more, see [here](#formats).

Double-sided missions have their back saved to `game/double_sided/`. First Edition is not supported.

## Basic Instructions

Navigate to the [root directory](../..) as plugins are not meant to be run in the [plugin directory](.).

If you're on macOS or Linux, open **Terminal**. If you're on Windows, open **PowerShell**.

Create and start your virtual Python environment and install Python dependencies if you have not done so already. See [here](../../README.md#basic-usage) for more information.

Put your decklist into a text file in [game/decklist](../game/decklist/). In this example, the filename is `deck.txt` and the decklist format is trekcc.org (`trekcc`).

Run the script.

```sh
python plugins/star_trek_ccg/fetch.py game/decklist/deck.txt trekcc
```

Now you can create the PDF using [`create_pdf.py`](../../README.md#create_pdfpy).

## CLI Options

```
Usage: fetch.py [OPTIONS] DECK_PATH {lackey|trekcc}

Options:
  --help  Show this message and exit.
```

## Formats

### `trekcc`

[trekcc.org](https://www.trekcc.org/decklists/) decklist text format. Cards are matched by their collector info, such as `55V027`.

```
Missions
Headquarters
54	V	9		•Earth, Cradle of the Federation
Planet
39	V	7		•Ba'ku Planet, Safeguard Civilization

Draw Deck (42)
Event
49	V	12		1x Change of Venue
2	R	35		2x Common Ground
Personnel
Federation
55	V	27		1x •Beverly Crusher, Principled Physician
55	V	34		2x •William T. Riker, Smooth Advocate

Dilemma Pile (40)
Dual
10	R	2		2x An Issue of Trust
22	V	7		3x Legacy
```

### `lackey`

[LackeyCCG](https://lackeyccg.com/) deck text format. Cards are matched by their LackeyCCG name.

```
1	Beverly Crusher Principled Physician
2	William T. Riker Smooth Advocate
2	Common Ground
Dilemmas:
2	An Issue of Trust
3	Legacy
Missions:
1	Earth Cradle of the Federation
1	Ba'ku Planet Safeguard Civilization
```
