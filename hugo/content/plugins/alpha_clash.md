---
title: 'Alpha Clash'
weight: 15
---

This plugin reads a decklist and puts the card images into the proper `game/` directories.

This plugin supports the `deckplanet` decklist format. To learn more, see [here](#formats).

Card images are fetched from [DeckPlanet](https://www.deckplanet.net/alpha_clash/card-db), the card database linked from the official Alpha Clash site. Contender, Clashground, and sideboard cards are included. Back faces of double-faced cards are saved to `game/double_sided/`.

## Basic Instructions

Navigate to the root directory as plugins are not meant to be run in the plugins directory.

If you're on macOS or Linux, open **Terminal**. If you're on Windows, open **PowerShell**.

Create and start your virtual Python environment and install Python dependencies if you have not done so already. See [here]({{% ref "../docs/create/#basic-usage" %}}) for more information.

Put your decklist into a text file in `game/decklist`. In this example, the filename is `deck.txt` and the decklist format is DeckPlanet (`deckplanet`).

Run the script.

```sh
python plugins/alpha_clash/fetch.py game/decklist/deck.txt deckplanet
```

Now you can create the PDF using [`create_pdf.py`]({{% ref "../docs/create" %}}).

## CLI Options

```
Usage: fetch.py [OPTIONS] DECK_PATH {deckplanet}

Options:
  --help  Show this message and exit.
```

## Formats

### `deckplanet`

[DeckPlanet](https://www.deckplanet.net/alpha_clash/dashboard) format. On a deck page, click **Export Deck**, then **Copy to Clipboard**.

```
Webber, Demolitions Agent [ST3-001]
4 Denver [AC1-001]
4 Moxie, Preparing for Battle [AC1-004]
3 Moxie, Alpha Hunting Specialist [AC1-006]
4 Moxie's Heavy Power Armor [AC1-018]
3 Alternative Strike [AC2-115]
2 Tactical Vest [AC3-023]
4 Suit Up! [AC3-027]
4 Machina, Scrap Blaster [AC3-122]
3 Crimson Scales [AC3-128]
2 Harvest of Souls [AC4-029]
2 Moxie, the Decisive [AC4-154]
4 Deflating [AC5-006]
3 Clarity, Bad Omen [AC5-008]
3 Clarity, From the Shadows [AC5-009]
2 Colonel Edwards, Mastermind [AC5-011]
4 Major Dean, Defender of Freedom [AC5-017]
1 Iron Piston [AC6-172]
4 Webber, Holding Ground [ST3-003]
4 Ultimate Power Armor [TP1-031]
---Sideboard---
```

The first line is the Contender and has no quantity, so one copy is fetched.
