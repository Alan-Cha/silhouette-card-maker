# Doomtown: Reloaded Plugin

This plugin reads a decklist, automatically fetches card art from [DoomtownDB](https://dtdb.co/) and puts them in the proper `game/` directories.

This plugin supports **DoomtownDB decklist URLs**. To learn more, see [here](#formats).

## Basic Instructions

Navigate to the [root directory](../..) as plugins are not meant to be run in the [plugin directory](.).

If you're on macOS or Linux, open **Terminal**. If you're on Windows, open **PowerShell**.

Create and start your virtual Python environment and install Python dependencies if you have not done so already. See [here](../../README.md#basic-usage) for more information.

Copy the URL of a published decklist from [DoomtownDB](https://dtdb.co/en/decklists) and save it into a text file in [game/decklist](../game/decklist/). In this example, the filename is `deck.txt` and the decklist format is DoomtownDB URL (`dtdb_url`).

Run the script.

```sh
python plugins/doomtown_reloaded/fetch.py game/decklist/deck.txt dtdb_url
```

Now you can create the PDF using [`create_pdf.py`](../../README.md#create_pdfpy).

## CLI Options

```
Usage: fetch.py [OPTIONS] DECK_PATH {dtdb_url}

Options:
  --help  Show this message and exit.
```

### Examples

You can also use the URL directly in the command line. Note the single quotes around the URL.

```sh
python plugins/doomtown_reloaded/fetch.py 'https://dtdb.co/en/decklist/3803/3-8-10-law-dogs' dtdb_url
```

## Formats

### `dtdb_url`

DoomtownDB URL format uses the full URL of a published decklist from [DoomtownDB](https://dtdb.co/en/decklists). Every card in the deck is fetched, including the outfit, legend, and jokers.

```
https://dtdb.co/en/decklist/3803/3-8-10-law-dogs
```

Private decks are not available through the DoomtownDB API, so publish your deck first.

## Notes

DoomtownDB card images are 300 x 420 pixels, so printed cards will be less sharp than plugins with high resolution scans.

DoomtownDB does not provide card back images. Put a card back image into `game/back/` if you want to print backs.

DoomtownDB covers the Alderac Entertainment Group releases and the Pine Box Entertainment releases through **Whispers of War**. Cards from sets that DoomtownDB has not added yet cannot be fetched.
