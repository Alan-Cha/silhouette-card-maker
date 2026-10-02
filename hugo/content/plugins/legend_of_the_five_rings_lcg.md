---
title: 'Legend of the Five Rings: The Card Game'
weight: 67
---

This plugin is for **Legend of the Five Rings: The Card Game** (LCG), originally by Fantasy Flight Games and now continued by the Emerald Legacy community.

This plugin reads a decklist, automatically fetches card art from [EmeraldDB](https://www.emeralddb.org/) and puts them in the proper `game/` directories. Every card in the deck is fetched, including the stronghold, role, and provinces.

This plugin supports **EmeraldDB deck URLs** and **EmeraldDB JSON**. To learn more, see [here](#formats).

## Basic Instructions

Navigate to the root directory as plugins are not meant to be run in the plugins directory.

If you're on macOS or Linux, open **Terminal**. If you're on Windows, open **PowerShell**.

Create and start your virtual Python environment and install Python dependencies if you have not done so already. See [here]({{% ref "../docs/create/#basic-usage" %}}) for more information.

**Important:** Legend of the Five Rings uses different card backs for dynasty, conflict, and province cards. The plugin fetches only the front images, so you must place the appropriate back image in `game/back/` before creating your PDF.

Open your deck on [EmeraldDB](https://www.emeralddb.org/decks) and copy its link from the address bar (or use **Link (This Version)** in the deck builder). Save the link into a text file in `game/decklist`. In this example, the filename is `deck.txt` and the decklist format is EmeraldDB URL (`emeralddb_url`).

Run the script.

```sh
python plugins/legend_of_the_five_rings_lcg/fetch.py game/decklist/deck.txt emeralddb_url
```

Now you can create the PDF using [`create_pdf.py`]({{% ref "../docs/create" %}}).

## CLI Options

```
Usage: fetch.py [OPTIONS] DECK_PATH {emeralddb_json|emeralddb_url}

Options:
  --help  Show this message and exit.
```

### Examples

You can also use the URL directly in the command line. Note the single quotes around the URL.

```sh
python plugins/legend_of_the_five_rings_lcg/fetch.py 'https://www.emeralddb.org/decks/75ffc2ba-93a2-4551-bab3-2bb12ce015d7' emeralddb_url
```

Use a saved EmeraldDB JSON file.

```sh
python plugins/legend_of_the_five_rings_lcg/fetch.py game/decklist/deck.json emeralddb_json
```

## Formats

### `emeralddb_url`

EmeraldDB URL format uses the full URL of a deck from [EmeraldDB](https://www.emeralddb.org).

```
https://www.emeralddb.org/decks/75ffc2ba-93a2-4551-bab3-2bb12ce015d7
```

### `emeralddb_json`

EmeraldDB decklist JSON, as returned by `https://www.emeralddb.org/api/decklists/<deck id>`. Card IDs map to quantities. If `card_pack_ids` is present, the image from that printing is used; otherwise the current printing is used.

```json
{
  "cards": {
    "fortress-at-the-sea-of-fire": 1,
    "keeper-of-earth": 1,
    "fine-katana": 3
  },
  "card_pack_ids": {
    "fine-katana": "emerald-core-set"
  }
}
```
