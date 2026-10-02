---
title: 'Battle Spirits Saga'
weight: 26
---

This plugin reads a decklist, fetches the card images, and puts the card images into the proper `game/` directories.

Card images come from the [official Battle Spirits Saga site](https://www.battlespirits-saga.com/cards/). Cards that are not on the official site, such as the `BSS07A` and `BSS07B` sets, are fetched from [bssdb.dev](https://www.bssdb.dev) instead. Battle Spirits Saga has no double-sided cards, so this plugin only puts images into `game/front/`.

This plugin supports the `bssdb` and `bssdb_tts` decklist formats. To learn more, see [here](#formats).

## Basic Instructions

Navigate to the root directory as plugins are not meant to be run in the plugins directory.

If you're on macOS or Linux, open **Terminal**. If you're on Windows, open **PowerShell**.

Create and start your virtual Python environment and install Python dependencies if you have not done so already. See [here]({{% ref "../docs/create/#basic-usage" %}}) for more information.

Put your decklist into a text file in `game/decklist`. In this example, the filename is `deck.txt` and the decklist format is bssdb.dev (`bssdb`).

Run the script.

```sh
python plugins/battle_spirits_saga/fetch.py game/decklist/deck.txt bssdb
```

Now you can create the PDF using [`create_pdf.py`]({{% ref "../docs/create" %}}).

## CLI Options

```
Usage: fetch.py [OPTIONS] DECK_PATH {bssdb|bssdb_tts}

Options:
  --help  Show this message and exit.
```

## Formats

Both formats come from the **Text Export** section of the [bssdb.dev](https://www.bssdb.dev) deck exporter. Cards in the sideboard are fetched too.

### `bssdb`

The **Text** tab of the bssdb.dev deck exporter.

```
=== Main Deck ===
3x BSS01-039-p1: Beldegor of the Dark World Seven
4x BSS01-118: Starblessed Draw
2x BSS01-127: Absolute Ice Shield
4x BSS01-122: Deadly Balance
3x ST02-002: Dragonaga Assassin
2x BSS01-125: Core Theft
4x BSS04-022: Mirrorcaster Ouroborsha
3x BSS04-023: Hakuja the Wizard
4x BSS03-024: Shaznake
1x BSS03-022: Viper Dragon Hsuan Falung
2x BSS02-028: Dark Knight Lamorak
4x BSS03-108: Amethyst Sanctuary
3x BSS04-120: Doubly Deadly
4x BSS01-108: Rotting Swamp
1x BSS01-038: Dread Knight Nemesis
4x BSS04-076: Barkmaiden Leucerium
2x BSS01-129: Counter Sword

=== Sideboard ===
3x ST03-015: Dream Bomb
2x BSS04-136: Raging Tide
1x ST06-014: Flood Stream
2x BSS01-038: Dread Knight Nemesis
2x PR-001: Ferrarl Slash
```

### `bssdb_tts`

The **Dexef's TTS** tab of the bssdb.dev deck exporter.

```
=== Main Deck ===
[BSS01-039_p1,BSS01-039_p1,BSS01-039_p1,BSS01-118,BSS01-118,BSS01-118,BSS01-118,BSS01-127,BSS01-127,BSS01-122,BSS01-122,BSS01-122,BSS01-122,ST02-002,ST02-002,ST02-002,BSS01-125,BSS01-125,BSS04-022,BSS04-022,BSS04-022,BSS04-022,BSS04-023,BSS04-023,BSS04-023,BSS03-024,BSS03-024,BSS03-024,BSS03-024,BSS03-022,BSS02-028,BSS02-028,BSS03-108,BSS03-108,BSS03-108,BSS03-108,BSS04-120,BSS04-120,BSS04-120,BSS01-108,BSS01-108,BSS01-108,BSS01-108,BSS01-038,BSS04-076,BSS04-076,BSS04-076,BSS04-076,BSS01-129,BSS01-129]

=== Sideboard ===
[ST03-015,ST03-015,ST03-015,BSS04-136,BSS04-136,ST06-014,BSS01-038,BSS01-038,PR-001,PR-001]
```
