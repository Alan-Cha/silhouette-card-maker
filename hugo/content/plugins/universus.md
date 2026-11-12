---
title: 'UniVersus'
weight: 115
---

This plugin reads a decklist, fetches the card images from [universus.cards](https://universus.cards), and puts the card images into the proper `game/` directories.

This plugin supports the `universus_url`, `universus_json`, and `universus_text` formats. To learn more, see [here](#formats).

The starting character is always included and listed first. Mainboard and sideboard cards are both fetched unless `--ignore_sideboard` is used. Maybeboard cards are never fetched. Double-sided cards have their back faces put into `game/double_sided/`.

Images come from [uvsultra.online](https://uvsultra.online) when it has a larger copy of the same card (744x1039 for recent sets), otherwise from universus.cards (358x500). Older sets are only available at about 358x500, which may print slightly soft.

## Basic Instructions

Navigate to the root directory as plugins are not meant to be run in the plugins directory.

If you're on macOS or Linux, open **Terminal**. If you're on Windows, open **PowerShell**.

Create and start your virtual Python environment and install Python dependencies if you have not done so already. See [here]({{% ref "../docs/create/#basic-usage" %}}) for more information.

Put your decklist into a text file in `game/decklist`. In this example, the filename is `deck.txt` and the decklist format is universus.cards URL (`universus_url`).

Run the script.

```sh
python plugins/universus/fetch.py game/decklist/deck.txt universus_url
```

Now you can create the PDF using [`create_pdf.py`]({{% ref "../docs/create" %}}).

## CLI Options

```
Usage: fetch.py [OPTIONS] DECK_PATH
                {universus_url|universus_json|universus_text}

Options:
  --ignore_sideboard  Skip sideboard cards when fetching cards.
  --help              Show this message and exit.
```

## Formats

### `universus_url`

[universus.cards](https://universus.cards) deck URL format. The deck must be public. Each line can contain one deck URL.

```
https://universus.cards/deck/e4c57177-8a10-40e6-9786-0cbf35268bd9
```

You can also use the URL directly in the command line. Note the single quotes around the URL.

```sh
python plugins/universus/fetch.py 'https://universus.cards/deck/e4c57177-8a10-40e6-9786-0cbf35268bd9' universus_url
```

### `universus_json`

[universus.cards](https://universus.cards) deck JSON format, the data returned when opening a deck URL without a browser. Each entry in `cards` is `[card id, mainboard count, sideboard count]`.

```json
{
  "name": "Ives Kailub (Reiner Braun)",
  "format": "Standard",
  "cards": [[10943, 1, 0], [10405, 1, 1], [10897, 3, 0], [11927, 0, 1]],
  "startingCharacter": 10943
}
```

### `universus_text`

[universus.cards](https://universus.cards) decklist text format. Open a deck, set **Display As** to **Decklist**, and copy the text. Each card is `<quantity> <name> | <set>`, and cards are looked up by name and set, so the first printing found in that set is used.

```
# Starting Character

1 Reiner Braun | Attack on Titan: Battle for Humanity

# Mainboard

## Action

1 Genkai's Guidance | Yu Yu Hakusho: Dark Tournament
3 Chomp | Attack on Titan: Battle for Humanity

# Sideboard

## Action

1 Filled with Doubt | Attack on Titan: Apocalypse

# Maybeboard
```
