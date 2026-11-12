---
title: 'Star Wars: The Card Game'
weight: 112
---

This plugin reads a decklist, automatically fetches card art from [SWLCGDB](https://swlcgdb.com/) and puts them in the proper `game/` directories.

This plugin supports SWLCGDB deck URLs. To learn more, see [here](#formats).

## Basic Instructions

Navigate to the root directory as plugins are not meant to be run in the plugins directory.

If you're on macOS or Linux, open **Terminal**. If you're on Windows, open **PowerShell**.

Create and start your virtual Python environment and install Python dependencies if you have not done so already. See [here]({{% ref "../docs/create/#basic-usage" %}}) for more information.

Copy the URL of your deck from [SWLCGDB](https://swlcgdb.com) and save it into a text file in `game/decklist`. In this example, the filename is `deck.txt` and the decklist format is SWLCGDB URL (`swlcgdb_url`).

Run the script.

```sh
python plugins/star_wars_lcg/fetch.py game/decklist/deck.txt swlcgdb_url
```

Now you can create the PDF using [`create_pdf.py`]({{% ref "../docs/create" %}}).

## CLI Options

```
Usage: fetch.py [OPTIONS] DECK_PATH {swlcgdb_url}

Options:
  --help  Show this message and exit.
```

### Examples

You can also use the URL directly in the command line. Note the single quotes around the URL.

```sh
python plugins/star_wars_lcg/fetch.py 'https://swlcgdb.com/decks/387' swlcgdb_url
```

## Formats

### `swlcgdb_url`

SWLCGDB URL format uses the full URL of a deck from [SWLCGDB](https://swlcgdb.com).

```
https://swlcgdb.com/decks/387
```

Every card from the deck's objective sets is fetched. SWLCGDB has no images for affiliation cards, so the affiliation card is not included.
