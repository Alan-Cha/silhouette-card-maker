# Sorcery: Contested Realm Plugin

This plugin reads a decklist, automatically fetches card art from [sorcerytcg.com](https://sorcerytcg.com/) (formerly [Curiosa](https://curiosa.io/)) and puts them in the proper `game/` directories.

This plugin supports deck URLs from [sorcerytcg.com](https://sorcerytcg.com/) and [Curiosa](https://curiosa.io/). To learn more, see [here](#formats).

## Basic Instructions

Navigate to the [root directory](../..) as plugins are not meant to be run in the [plugin directory](.).

If you're on macOS or Linux, open **Terminal**. If you're on Windows, open **PowerShell**.

Create and start your virtual Python environment and install Python dependencies if you have not done so already. See [here](../../README.md#basic-usage) for more information.

Put your decklist into a text file in [game/decklist](../game/decklist/). In this example, the filename is `deck.txt` and the decklist format is a deck URL (`curiosa_url`).

Run the script.

```sh
python plugins/sorcery_contested_realm/fetch.py game/decklist/deck.txt curiosa_url
```

Now you can create the PDF using [`create_pdf.py`](../../README.md#create_pdfpy).

## Card Backs

Sorcery has two card backs: spellbook cards have one back, and Sites (atlas cards) have another.

Put the spellbook card back in [game/back](../../game/back/). Then pass the atlas card back with `--atlas_back`. The plugin saves a copy of the atlas back in [game/double_sided](../../game/double_sided/) for each Site, so one PDF prints both backs.

```sh
python plugins/sorcery_contested_realm/fetch.py game/decklist/deck.txt curiosa_url --atlas_back atlas_back.png
```

Card images show Sites in portrait orientation. If the atlas back image is landscape, the plugin turns it to portrait to match.

## CLI Options

```
Usage: fetch.py [OPTIONS] DECK_PATH {curiosa_url}

Options:
  --atlas_back FILE  The path to an atlas card back image. Sites get this back
                     in game/double_sided/. Put the spellbook card back in
                     game/back/.
  --help             Show this message and exit.
```

## Formats

### `curiosa_url`

Curiosa URL format uses the full URL of a public deck from [sorcerytcg.com](https://sorcerytcg.com/). Curiosa deck URLs still work, because Curiosa moved to sorcerytcg.com and kept its deck IDs.

```
https://sorcerytcg.com/decks/cme5x329q00k9jo04ouuycsek
https://curiosa.io/decks/cme5x329q00k9jo04ouuycsek
```

You can also use the URL directly in the command line. Note the single quotes around the URL.

```sh
python plugins/sorcery_contested_realm/fetch.py 'https://sorcerytcg.com/decks/cme5x329q00k9jo04ouuycsek' curiosa_url
```
