---
title: 'Warhammer 40,000: Conquest'
weight: 115
---

This plugin reads a decklist, automatically fetches card art from [ConquestDB](https://www.conquestdb.com/) and puts them in the proper `game/` directories.

This plugin supports the ConquestDB decklist download and ConquestDB deck URLs. To learn more, see [here](#formats).

## Basic Instructions

Navigate to the root directory as plugins are not meant to be run in the plugins directory.

If you're on macOS or Linux, open **Terminal**. If you're on Windows, open **PowerShell**.

Create and start your virtual Python environment and install Python dependencies if you have not done so already. See [here]({{% ref "../docs/create/#basic-usage" %}}) for more information.

Download your deck from [ConquestDB](https://www.conquestdb.com) (**Download Deck** on any deck page) and save it into `game/decklist`. In this example, the filename is `deck.txt` and the decklist format is ConquestDB (`conquestdb`).

Run the script.

```sh
python plugins/warhammer_40k_conquest/fetch.py game/decklist/deck.txt conquestdb
```

The warlord's bloodied side is saved into `game/double_sided/`.

Now you can create the PDF using [`create_pdf.py`]({{% ref "../docs/create" %}}).

## CLI Options

```
Usage: fetch.py [OPTIONS] DECK_PATH {conquestdb|conquestdb_url}

Options:
  --help  Show this message and exit.
```

### Examples

Use a ConquestDB deck link saved into a text file instead of a downloaded deck.

```sh
python plugins/warhammer_40k_conquest/fetch.py game/decklist/deck.txt conquestdb_url
```

You can also use the URL directly in the command line. Note the single quotes around the URL.

```sh
python plugins/warhammer_40k_conquest/fetch.py 'https://www.conquestdb.com/decks/Echo/Zq99g5gmBTdfq8cg/' conquestdb_url
```

## Formats

### `conquestdb`

[ConquestDB](https://www.conquestdb.com) deck download format. Download from any deck page using **Download Deck**.

The warlord is the first line after the first separator. Every other card is a `{quantity}x {name}` line, so a plain list of `{quantity}x {name}` lines also works.

```
Square root of 7 kyubed
----------------------------------------------------------------------
Grigory Maksim
Astra Militarum
----------------------------------------------------------------------
Signature Squad

4x Maksim's Squadron
1x Clearing the Path
2x Keep Firing!
1x Searchlight
----------------------------------------------------------------------
Army

3x Krieg Armoured Regiment
3x Pattern IX Immolator
```

### `conquestdb_url`

ConquestDB URL format uses the full URL of a deck from [ConquestDB](https://www.conquestdb.com).

```
https://www.conquestdb.com/decks/Echo/Zq99g5gmBTdfq8cg/
```
