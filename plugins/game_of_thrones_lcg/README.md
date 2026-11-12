# A Game of Thrones: The Card Game Plugin

This plugin reads a decklist for **A Game of Thrones: The Card Game (Second Edition)**, automatically fetches card art from [ThronesDB](https://thronesdb.com/) and puts them in the proper `game/` directories.

This plugin supports **ThronesDB decklist URLs** and **ThronesDB JSON**. To learn more, see [here](#formats).

## Basic Instructions

Navigate to the [root directory](../..) as plugins are not meant to be run in the [plugin directory](.).

If you're on macOS or Linux, open **Terminal**. If you're on Windows, open **PowerShell**.

Create and start your virtual Python environment and install Python dependencies if you have not done so already. See [here](../../README.md#basic-usage) for more information.

Copy the URL of a published decklist from [ThronesDB](https://thronesdb.com/decklists). In this example, the decklist format is ThronesDB URL (`thronesdb_url`). Note the single quotes around the URL.

Run the script.

```sh
python plugins/game_of_thrones_lcg/fetch.py 'https://thronesdb.com/decklist/view/1' thronesdb_url
```

Now you can create the PDF using [`create_pdf.py`](../../README.md#create_pdfpy).

Plot cards are rotated to portrait so they can be laid out alongside the rest of the deck. The agenda is included, but the faction card is not, as ThronesDB has no image for it.

## CLI Options

```
Usage: fetch.py [OPTIONS] DECK_PATH {thronesdb_json|thronesdb_url}

Options:
  --help  Show this message and exit.
```

### Examples

Use a ThronesDB decklist link saved into a text file in [game/decklist](../game/decklist/).

```sh
python plugins/game_of_thrones_lcg/fetch.py game/decklist/deck.txt thronesdb_url
```

Use ThronesDB JSON saved into a file.

```sh
python plugins/game_of_thrones_lcg/fetch.py game/decklist/deck.json thronesdb_json
```

## Formats

### `thronesdb_json`

[ThronesDB](https://thronesdb.com) public API decklist format. Open `https://thronesdb.com/api/public/decklist/<id>` in your browser, where `<id>` is the number in the decklist URL, and save the page into a file. Only `slots` is used.

```json
{
  "faction_code": "lannister",
  "slots": {
    "01003": 1,
    "01028": 2,
    "01205": 1
  },
  "agendas": ["01205"]
}
```

### `thronesdb_url`

ThronesDB URL format uses the full URL of a published decklist from [ThronesDB](https://thronesdb.com). Private decks (`/deck/view/`) are not available through the ThronesDB public API, so publish the deck first.

```
https://thronesdb.com/decklist/view/1
https://thronesdb.com/decklist/view/1/secrets-and-schemes-1-core-set-1.0
```
