# WIXOSS Plugin

This plugin reads a decklist, fetches the card images from the [official WIXOSS English card list](https://www.takaratomy.co.jp/products/en.wixoss/card/), and puts the card images into the proper `game/` directories.

Both the LRIG deck and the main deck are fetched. PIECE cards, which are printed landscape, are rotated to portrait.

This plugin supports the `wixosstcg_url` format. To learn more, see [here](#formats).

## Basic Instructions

Navigate to the [root directory](../..) as plugins are not meant to be run in the [plugin directory](.).

If you're on macOS or Linux, open **Terminal**. If you're on Windows, open **PowerShell**.

Create and start your virtual Python environment and install Python dependencies if you have not done so already. See [here](../../README.md#basic-usage) for more information.

Put your decklist into a text file in [game/decklist](../game/decklist/). In this example, the filename is `deck.txt` and the decklist format is wixosstcg.eu URL (`wixosstcg_url`).

Run the script.

```sh
python plugins/wixoss/fetch.py game/decklist/deck.txt wixosstcg_url
```

Now you can create the PDF using [`create_pdf.py`](../../README.md#create_pdfpy).

## CLI Options

```
Usage: fetch.py [OPTIONS] DECK_PATH {wixosstcg_url}

Options:
  --help  Show this message and exit.
```

## Formats

### `wixosstcg_url`

wixosstcg.eu URL format uses the full URL of a public deck from the [wixosstcg.eu deckbuilder](https://www.wixosstcg.eu/decks).

```
https://www.wixosstcg.eu/deck/19427/Carnival_P15
```

You can also use the URL directly in the command line. Note the single quotes around the URL.

```sh
python plugins/wixoss/fetch.py 'https://www.wixosstcg.eu/deck/19427/Carnival_P15' wixosstcg_url
```

Cards that are not in the official English card list cannot be fetched and are listed as errors.
