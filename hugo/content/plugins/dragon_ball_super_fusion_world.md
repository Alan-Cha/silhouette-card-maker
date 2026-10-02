---
title: 'Dragon Ball Super Card Game Fusion World'
weight: 31
---

This plugin reads a decklist, fetches the card images from the [official card list](https://www.dbs-cardgame.com/fw/en/cardlist/), and puts the card images into the proper `game/` directories.

Leader cards are double-sided, so their back (awakened) side is put into `game/double_sided/`.

This plugin supports the `fusionworld` and `deckplanet` decklist formats. To learn more, see [here](#formats).

## Basic Instructions

Navigate to the root directory as plugins are not meant to be run in the plugins directory.

If you're on macOS or Linux, open **Terminal**. If you're on Windows, open **PowerShell**.

Create and start your virtual Python environment and install Python dependencies if you have not done so already. See [here]({{% ref "../docs/create/#basic-usage" %}}) for more information.

Put your decklist into a text file in `game/decklist`. In this example, the filename is `deck.txt` and the decklist format is `fusionworld`.

Run the script.

```sh
python plugins/dragon_ball_super_fusion_world/fetch.py game/decklist/deck.txt fusionworld
```

Now you can create the PDF using [`create_pdf.py`]({{% ref "../docs/create" %}}).

## CLI Options

```
Usage: fetch.py [OPTIONS] DECK_PATH {fusionworld|deckplanet}

Options:
  --help  Show this message and exit.
```

## Formats

### `fusionworld`

The deck text exported by **Fusion World Digital**, [Egman Events](https://deckbuilder.egmanevents.com/fusionworld) (**Deck Toolkit** > **Text**), [dragonball.gg](https://dragonball.gg) and [DeckPlanet](https://www.deckplanet.net/fusion_world)'s **Fusion World Digital** and **TCGArena** exports. The leader is the line without a quantity, and the number in parentheses after each name is the Fusion World Digital card ID.

```
Name (Exported)
FS01-01 Son Goku(2)
4 FS01-03 Master Roshi(5)
4 FS01-02 Whis(4)
4 FS01-10 Tien Shinhan(12)
2 FS01-04 Krillin(6)
```

It also accepts the [Limitless TCG](https://docs.limitlesstcg.com/player/decklists) style of a quantity followed by a card number.

```
1 FB01-001
4 FS01-03
4 FB01-005
3 FS01-04
4 FB01-014
```

The quantity may also be written with an `x` (`4xFB01-005` or `4 x FB01-005`), and any text after the card number (such as the card name) is ignored. Lines that don't match, such as section headers, are skipped.

To use a parallel (alternate art) printing, add its suffix to the card number, such as `FB01-004_p1`.

### `deckplanet`

[DeckPlanet](https://www.deckplanet.net/fusion_world)'s default **Copy to Clipboard** export. The leader is the line without a quantity.

```
Son Goku [FB01-001]
4 Son Goku [FB01-005]
4 Vegeta [FB01-014]
3 Krillin [FS01-04]
Sideboard
2 Piccolo [FB01-008]
```

Sideboard cards are fetched too.
