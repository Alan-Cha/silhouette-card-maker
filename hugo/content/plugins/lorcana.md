---
title: 'Lorcana'
weight: 70
---

This plugin reads a decklist, automatically fetches card art from [Lorcast](https://lorcast.com) or [Dreamborn](https://dreamborn.ink) and puts them in the proper `game/` directories.

This plugin supports decklist exports from [Dreamborn.ink](https://dreamborn.ink). To learn more, see [here](#formats).

## Basic Instructions

Navigate to the root directory as plugins are not meant to be run in the plugins directory.

If you're on macOS or Linux, open **Terminal**. If you're on Windows, open **PowerShell**.

Create and start your virtual Python environment and install Python dependencies if you have not done so already. See [here]({{% ref "../docs/create/#basic-usage" %}}) for more information.

Put your decklist into a text file in `game/decklist`. In this example, the filename is `deck.txt` and the decklist format is Dreamborn (`dreamborn`).

Run the script.

```shell
python plugins/lorcana/fetch.py game/decklist/deck.txt dreamborn
```

Now you can create the PDF using [`create_pdf.py`]({{% ref "../docs/create" %}}).

## CLI Options

```
Usage: fetch.py [OPTIONS] DECK_PATH {dreamborn}

Options:
  --source [dreamborn|lorcast]  Source of the deck list (default: "dreamborn"
                                if --lang is specified, otherwise "lorcast")
  --lang [en|fr|de|it|es|ja]    Language code for card images (default: "en")
  --help                        Show this message and exit.
```

## Formats

### `dreamborn`

[Dreamborn](https://dreamborn.ink) format.

```
1 Elsa, Spirit of Winter
4 Magic Broom, Illuminary Keeper
4 Diablo - Obedient Raven
4 Mr. Smee, Bumbling Mate
1 Anna - True-Hearted *E*
4 Pete - Games Referee
4 Merlin, Goat
```

#### Special Variant Artwork

Dreamborn does not natively have a way to select special variant artwork for cards. Besides their normal printing, some cards also have a special variant with alternate artwork, at one of the following rarities: Enchanted, Epic, Iconic, or Promo (e.g. [Max Goof - Rockin' Teen](https://dreamborn.ink/cards/max-goof/rockin-teen), [Kuzco - Temperamental Emperor](https://dreamborn.ink/cards/kuzco/temperamental-emperor)).

You can select a variant by adding one of the following markers at the end of the card line:

| Marker | Variant |
|--------|---------|
| `*E*` | Enchanted |
| `*ENCHANTED*` | Enchanted |
| `*EP*` | Epic |
| `*EPIC*` | Epic |
| `*I*` | Iconic |
| `*ICONIC*` | Iconic |
| `*P*` | Promo |
| `*PROMO*` | Promo |

```diff
- 1 Elsa, Spirit of Winter
+ 1 Elsa, Spirit of Winter *E*
```

```diff
- 1 Max Goof - Rockin' Teen
+ 1 Max Goof - Rockin' Teen *EPIC*
```

```diff
- 1 Kuzco - Temperamental Emperor
+ 1 Kuzco - Temperamental Emperor *PROMO*
```

#### Selecting a Specific Print

Some cards have more than one distinct promo printing (e.g. [Mickey Mouse - True Friend](https://dreamborn.ink/cards/mickey-mouse/true-friend) has separate P1, P2, and P3 promo prints). Since `*PROMO*` can't tell these apart, you can instead select the exact printing by its set code, optionally followed by its collector number (needed when a single promo set has more than one print of the same card).

```diff
- 1 Mickey Mouse - True Friend
+ 1 Mickey Mouse - True Friend *P1*
```

```diff
- 1 Mickey Mouse - True Friend
+ 1 Mickey Mouse - True Friend *P2-15*
```

You can find a card's set code and collector number on its [Lorcast](https://lorcast.com) or [Dreamborn](https://dreamborn.ink) page (e.g. `#15/P2` means collector number `15` in set `P2`).