---
title: 'Middle-earth CCG'
weight: 87
---

This plugin is for **Middle-earth: The Wizards** and the rest of the **Middle-earth Collectible Card Game** (MECCG) by Iron Crown Enterprises (1995). It should not be confused with the **Lord of the Rings Trading Card Game** by Decipher or **The Lord of the Rings: The Card Game** by Fantasy Flight Games.

This plugin reads a decklist, finds each card in the [Council of Elrond cards database](https://github.com/council-of-elrond-meccg/meccg-cards-database), fetches the card images from [MeCCG Remaster](https://github.com/council-of-rivendell/meccg-remaster) and puts them in the proper `game/` directories.

This plugin supports the Cardnum decklist format, which is also used by GCCG and [play.meccg.com](https://play.meccg.com). To learn more, see [here](#formats).

## Basic Instructions

Navigate to the root directory as plugins are not meant to be run in the plugin directory.

If you're on macOS or Linux, open **Terminal**. If you're on Windows, open **PowerShell**.

Create and start your virtual Python environment and install Python dependencies if you have not done so already. See [here]({{% ref "../docs/create/#basic-usage" %}}) for more information.

All MECCG cards share the same card back. If you want to print backs, put a card back image in `game/back` before creating your PDF. The plugin fetches only the front images.

Put your decklist into a text file in `game/decklist`. In this example, the filename is `deck.txt` and the decklist format is Cardnum (`cardnum`).

Run the script.

```sh
python plugins/middle_earth_ccg/fetch.py game/decklist/deck.txt cardnum
```

Now you can create the PDF using [`create_pdf.py`]({{% ref "../docs/create" %}}).

## CLI Options

```
Usage: fetch.py [OPTIONS] DECK_PATH {cardnum}

Options:
  --remaster  Use the higher resolution MeCCG Remaster images instead of the
              original card art.
  --help      Show this message and exit.
```

By default, the plugin uses the original English card art. The `--remaster` option uses the community remastered English cards instead, which have a higher resolution and updated card text.

### Examples

Use the remastered card images.

```sh
python plugins/middle_earth_ccg/fetch.py game/decklist/deck.txt cardnum --remaster
```

## Formats

### `cardnum`

Cardnum format is the decklist format exported by [Cardnum](https://cardnum.net) and used by GCCG `.meccg` deck files and [play.meccg.com](https://play.meccg.com). Each line is a quantity, a card name, an optional alignment such as `[H]` (hero) or `[M]` (minion), and an optional set code such as `(TW)`.

```
Pool
1 Glorfindel II (TW)
1 Sam Gamgee (TW)

Characters
3 Saruman [H] (TW)

Resources
2 Dark Quarrels (TW)

Hazards
3 Cave-drake

Sideboard
1 Twilight (LE)

Sites
1 Rivendell [H] (TW)
```

Every section is fetched, including the pool, sideboard, and sites. Section headers and the GCCG `Notes` section are ignored.

Set codes are `TW` (The Wizards), `TD` (The Dragons), `DM` (Dark Minions), `LE` (The Lidless Eye), `AS` (Against the Shadow), `WH` (The White Hand), and `BA` (The Balrog).

If a card has several printings that match, the regular printing from the earliest set is used. If a card name has different versions, such as the hero and minion versions of Rivendell, the line must include an alignment or a set code that picks one version. Otherwise, the plugin prints an error listing the candidates.
