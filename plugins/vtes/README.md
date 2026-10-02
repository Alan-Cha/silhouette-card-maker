# Vampire: The Eternal Struggle Plugin

This plugin reads a decklist, automatically fetches card art from [KRCG](https://api.krcg.org/) and puts them in the proper `game/` directories.

This plugin supports the **text** decklist format used by the TWDA, Amaranth, VDB, and Lackey, and **TWDA** deck IDs. To learn more, see [here](#formats).

## Basic Instructions

Navigate to the [root directory](../..) as plugins are not meant to be run in the [plugin directory](.).

If you're on macOS or Linux, open **Terminal**. If you're on Windows, open **PowerShell**.

Create and start your virtual Python environment and install Python dependencies if you have not done so already. See [here](../../README.md#basic-usage) for more information.

Put your decklist into a text file in [game/decklist](../game/decklist/). In this example, the filename is `deck.txt` and the decklist format is text (`text`).

Run the script.

```sh
python plugins/vtes/fetch.py game/decklist/deck.txt text
```

Now you can create the PDF using [`create_pdf.py`](../../README.md#create_pdfpy).

Crypt and library cards have different backs. To print backs, fetch the crypt and the library into separate runs, each with its own back image in `game/back/`.

## CLI Options

```
Usage: fetch.py [OPTIONS] DECK_PATH {text|twda}

Options:
  --help  Show this message and exit.
```

### Examples

Use a deck from the [Tournament Winning Deck Archive](https://vdb.im/twd) by its ID.

```sh
python plugins/vtes/fetch.py 2016gncbg twda
```

## Formats

### `text`

Text format exported by [Amaranth](https://amaranth.vtes.co.nz), [VDB](https://vdb.im), and Lackey, and used by the TWDA. Crypt lines use the group column to pick the right vampire, including advanced (`ADV`) vampires. Lines that are not cards are skipped.

```
Crypt (12 cards, min=8, max=21, avg=3.75)
-----------------------------------------
2x Stick               3  ANI                      Nosferatu antitribu:4
1x Theo Bell (ADV)     7  CEL DOM POT pre          Brujah:2

Library (90 cards)
Master (12)
5x Blood Doll
1x Rack, The
```

Lackey decklists use a tab instead of `x` after the quantity.

```
5	Blood Doll
Crypt:
2	Stick
```

### `twda`

[TWDA](https://vdb.im/twd) deck ID, or a URL ending with it, fetched from [KRCG](https://api.krcg.org/). It can be passed directly in the command line or saved into a text file.

```
2016gncbg
https://api.krcg.org/twda/2016gncbg
https://vdb.im/decks/2016gncbg
```
