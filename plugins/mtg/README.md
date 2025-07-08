# MTG Plugin

This plugin reads a decklist and automatically fetches the card art and puts them in the proper `game/` directories.

This plugin supports many decklist formats such as, `simple`, `mtga`, `mtgo`, `archidekt`, `deckstats`, `moxfield`, and `scryfall_json`. To learn more, see [here](#formats).

## Basic instructions

Navigate to the [root directory](../..). This plugin is not meant to be run in `plugins/mtg/`.

If you're on macOS or Linux, open **Terminal**. If you're on Windows, open **PowerShell**.

Create and start your virtual Python environment and install Python dependencies if you have not done so already. See [here](../../README.md#basic-instructions) for more information.

Put your decklist into a text file in `game/decklist`. In this example, the filename is `deck.txt` and the decklist format is MTG Arena (`mtga`).

Run the script.

```sh
python plugins/mtg/fetch.py game/decklist/deck.txt mtga
```

Now you can create the PDF using [`create_pdf.py`](../../README.md#create_pdfpy).

## CLI Options

```
Usage: fetch.py [OPTIONS] DECK_PATH
                {simple|mtga|mtgo|archidekt|deckstats|moxfield}

Options:
  -i, --ignore_set_and_collector_number
                                  Ignore provided sets and collector numbers
                                  when fetching cards.
  --prefer_older_sets             Prefer fetching cards from older sets if
                                  sets are not provided.
  -s, --prefer_set TEXT           Prefer fetching cards from a particular
                                  set(s) if sets are not provided. Use this
                                  option multiple times to specify multiple
                                  preferred sets.
  --prefer_showcase               Prefer fetching cards with showcase
                                  treatment
  --prefer_extra_art               Prefer fetching cards with full art,
                                  borderless, or extended art.
  --help                          Show this message and exit.
```

### Examples

Use a Moxfield decklist named `my_decklist.txt`.

```sh
python plugins/mtg/fetch.py game/decklist/my_decklist.txt moxfield
```

Use a Moxfield decklist named `my_decklist.txt` and ignore all the provided sets and collector numbers. Instead, get the latest normal versions of these cards (not showcase or full/borderless/extended art).

```sh
python plugins/mtg/fetch.py game/decklist/my_decklist.txt moxfield -i
```

Use a Moxfield decklist named `my_decklist.txt` and ignore all the provided sets and collector numbers. Instead, get the latest full, borderless, or extended art for all cards when possible.

```sh
python plugins/mtg/fetch.py game/decklist/my_decklist.txt moxfield -i --prefer_extra_art
```

Use an MTG Online decklist named `old_school.txt` and ignore all the provided sets and collector numbers. Instead, get the latest oldest normal versions of these cards (not showcase or full/borderless/extended art).

```sh
python plugins/mtg/fetch.py game/decklist/old_school.txt mtgo -i --prefer_older_sets
```

Use a Deckstats decklist named `eldraine_commander.txt`. Use the set and collector numbers when provided. If not, get art from the Eldraine (`ELD`) and Wilds of Eldraine (`WOE`) expansions when possible.

```sh
python plugins/mtg/fetch.py game/decklist/eldraine_commander.txt deckstats -s eld -s woe
```

## Formats

### `simple`

A list of card names.

```
Isshin, Two Heavens as One
Arid Mesa
Battlefield Forge
Blazemire Verge
Blightstep Pathway
```

### `mtga`

Magic: The Gathering Arena format.

```
About
Name Death & Taxes

Companion
1 Yorion, Sky Nomad

Deck
2 Arid Mesa
1 Lion Sash
1 Loran of the Third Path
2 Witch Enchanter
```

### `mtgo`

Magic: The Gathering Online format.

```
1 Ainok Bond-Kin
1 Angel of Condemnation
2 Witch Enchanter

SIDEBOARD:
1 Containment Priest
3 Deafening Silence
```

### `archidekt`

Archidekt format.

```
1x Agadeem's Awakening // Agadeem, the Undercrypt (znr) 90 [Resilience,Land]
1x Ancient Cornucopia (big) 16 [Maybeboard{noDeck}{noPrice},Mana Advantage]
1x Arachnogenesis (cmm) 647 [Maybeboard{noDeck}{noPrice},Mass Disruption]
1x Ashnod's Altar (ema) 218 *F* [Mana Advantage]
1x Assassin's Trophy (sld) 139 [Targeted Disruption]
```

### `deckstats`

Deckstats format.

```
//Main
1 [2XM#310] Ash Barrens
1 Blinkmoth Nexus
1 Bloodstained Mire

//Sideboard
1 [2XM#315] Darksteel Citadel

//Maybeboard
1 [MID#159] Smoldering Egg // Ashmouth Dragon
```

### `moxfield`

Moxfield format.

```
1 Ainok Bond-Kin (2X2) 5
1 Pegasus Guardian // Rescue the Foal (CLB) 36
2 Witch Enchanter // Witch-Blessed Meadow (MH3) 239

SIDEBOARD:
1 Containment Priest (M21) 13
1 Deafening Silence (MB2) 9
```

### `scryfall_json`

Scryfall JSON format.

```json
{
  "entries": {
    "mainboard": [
      {
        "object": "deck_entry",
        "id": "ad26be56-051c-48f0-92ec-f99da16af903",
        "deck_id": "3e3f8810-6143-4036-a5a7-9c9f07a5e2e3",
        "section": "mainboard",
        "cardinality": 485.5,
        "count": 4,
        "raw_text": "4 Lightning Bolt",
        "found": true,
        "printing_specified": false,
        "finish": null,
        "card_digest": {
          "object": "card_digest",
          "id": "77c6fa74-5543-42ac-9ead-0e890b188e99",
          "oracle_id": "4457ed35-7c10-48c8-9776-456485fdf070",
          "name": "Lightning Bolt",
          "scryfall_uri": "https://scryfall.com/card/clu/141/lightning-bolt",
          "mana_cost": "{R}",
          "type_line": "Instant",
          "collector_number": "141",
          "set": "clu",
          "image_uris": {
            "front": "https://cards.scryfall.io/large/front/7/7/77c6fa74-5543-42ac-9ead-0e890b188e99.jpg?1706239968"
          }
        }
      }
    ]
  }
}
```