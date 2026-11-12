# Marvel Champions: The Card Game Plugin

This plugin reads a decklist, automatically fetches card art from [MarvelCDB](https://marvelcdb.com/) and puts them in the proper `game/` directories.

This plugin supports **MarvelCDB JSON** and **MarvelCDB deck URLs**. To learn more, see [here](#formats).

## Basic Instructions

Navigate to the [root directory](../..) as plugins are not meant to be run in the [plugin directory](.).

If you're on macOS or Linux, open **Terminal**. If you're on Windows, open **PowerShell**.

Create and start your virtual Python environment and install Python dependencies if you have not done so already. See [here](../../README.md#basic-usage) for more information.

Copy the URL of your deck or published decklist from [MarvelCDB](https://marvelcdb.com) and save it into [game/decklist](../game/decklist/). In this example, the filename is `deck.txt` and the decklist format is MarvelCDB URL (`marvelcdb_url`).

Run the script.

```sh
python plugins/marvel_champions/fetch.py game/decklist/deck.txt marvelcdb_url
```

Now you can create the PDF using [`create_pdf.py`](../../README.md#create_pdfpy).

The hero card is included automatically, with its alter-ego placed in `game/double_sided/`. Landscape cards, such as main schemes, are rotated to portrait.

Reprints use the image of the original printing. If MarvelCDB has no image for a card, the plugin tries the image store of Cerebro, the community Marvel Champions Discord bot, instead. Cards from the newest packs may not have an image anywhere yet; these are skipped and reported at the end of the run.

## CLI Options

```
Usage: fetch.py [OPTIONS] DECK_PATH {marvelcdb_json|marvelcdb_url}

Options:
  --help  Show this message and exit.
```

### Examples

You can also use the URL directly in the command line. Note the single quotes around the URL.

```sh
python plugins/marvel_champions/fetch.py 'https://marvelcdb.com/decklist/view/1' marvelcdb_url
```

Use a MarvelCDB deck JSON file instead of a URL.

```sh
python plugins/marvel_champions/fetch.py game/decklist/deck.json marvelcdb_json
```

## Formats

### `marvelcdb_json`

[MarvelCDB](https://marvelcdb.com) deck JSON, as returned by the MarvelCDB public API (for example, `https://marvelcdb.com/api/public/decklist/1.json`).

```json
{
  "hero_code": "01001a",
  "slots": {
    "01002": 1,
    "01003": 1,
    "01074": 2
  }
}
```

### `marvelcdb_url`

MarvelCDB URL format uses the full URL of a deck or published decklist from [MarvelCDB](https://marvelcdb.com). Personal decks must have public sharing enabled.

```
https://marvelcdb.com/deck/view/12345
https://marvelcdb.com/decklist/view/12345/deck-name-1.0
```
