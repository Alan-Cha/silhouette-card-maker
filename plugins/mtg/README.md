# MTG Plugin

This plugin reads a decklist and automatically fetches the card art and puts them in the proper `game/` directories.

This plugin supports many decklist formats such as `simple`, `mtga`, `mtgo`, `archidekt`, `cubecobra_csv`, `deckstats`, `moxfield`, `scryfall_json`, `mpcfill_xml`, and `url`. To learn more, see [here](#formats).

## Basic Instructions

Navigate to the [root directory](../..) as plugins are not meant to be run in the [plugin directory](.).

If you're on macOS or Linux, open **Terminal**. If you're on Windows, open **PowerShell**.

Create and start your virtual Python environment and install Python dependencies if you have not done so already. See [here](../../README.md#basic-usage) for more information.

Put your decklist into a text file in [game/decklist](../game/decklist/). In this example, the filename is `deck.txt` and the decklist format is MTG Arena (`mtga`).

Run the script.

```sh
python plugins/mtg/fetch.py game/decklist/deck.txt mtga
```

Now you can create the PDF using [`create_pdf.py`](../../README.md#create_pdfpy).

## CLI Options

```
Usage: fetch.py [OPTIONS] DECK_PATH {archidekt|cubecobra_csv|deckstats|moxfield|mpcfill_xml|mtga|mtgo|scryfall_json|simple|url}

Options:
  -i, --ignore_set_and_collector_number
                                  Ignore provided sets and collector numbers
                                  when fetching cards.
  --prefer_older_sets             Prefer fetching cards from older sets if
                                  sets are not provided.
  -s, --prefer_set TEXT           Prefer fetching cards from a particular
                                  set(s) if sets are not provided. Use this
                                  option multiple times for a priority list.
  --ignore_set TEXT               Exclude a set from consideration when
                                  fetching cards. Use this option multiple
                                  times to exclude multiple sets.
  --prefer_showcase               Prefer fetching cards with showcase
                                  treatment
  --prefer_extra_art              Prefer fetching cards with full art,
                                  borderless, or extended art.
  --prefer_lang [en|sp|fr|de|it|pt|jp|kr|ru|cs|ct|ag|ph]
                                  Preferred language for card images (printed
                                  code). Use multiple times for a priority list.
                                  Falls back to English if none are available.
  --prefer_ub                     Prefer Universe Beyond printings when
                                  available.
  --ignore_ub                     Exclude Universe Beyond printings from
                                  consideration.
  --tokens                        Fetch related tokens when fetching cards
  --exclude_basics                Skip basic lands (including Wastes and Snow-
                                  Covered basics).
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

Use an MTG Arena decklist named `deck.txt` and fetch Japanese card images where available, falling back to English otherwise.

```sh
python plugins/mtg/fetch.py game/decklist/deck.txt mtga --prefer_lang jp
```

Use an MTG Arena decklist named `deck.txt` and try Japanese first, then German, then English.

```sh
python plugins/mtg/fetch.py game/decklist/deck.txt mtga --prefer_lang jp --prefer_lang de
```

Use a Deckstats decklist named `eldraine_commander.txt` and prefer Eldraine first, then Wilds of Eldraine.

```sh
python plugins/mtg/fetch.py game/decklist/eldraine_commander.txt deckstats -s eld -s woe
```

Use an MTG Arena decklist named `deck.txt` and prefer Universe Beyond printings where available (e.g. Lord of the Rings, Warhammer 40K crossover cards).

```sh
python plugins/mtg/fetch.py game/decklist/deck.txt mtga --prefer_ub
```

Use an MTG Arena decklist named `deck.txt` and exclude Universe Beyond printings, always fetching standard Magic printings instead.

```sh
python plugins/mtg/fetch.py game/decklist/deck.txt mtga --ignore_ub
```

Use an MTG Arena decklist named `deck.txt` and skip basic lands, for example if you already own enough of them. This applies to every format except `mpcfill_xml`.

```sh
python plugins/mtg/fetch.py game/decklist/deck.txt mtga --exclude_basics
```

## Formats

### `archidekt`

[Archidekt](https://archidekt.com) format.

```
1x Agadeem's Awakening // Agadeem, the Undercrypt (znr) 90 [Resilience,Land]
1x Ancient Cornucopia (big) 16 [Maybeboard{noDeck}{noPrice},Mana Advantage]
1x Arachnogenesis (cmm) 647 [Maybeboard{noDeck}{noPrice},Mass Disruption]
1x Ashnod's Altar (ema) 218 *F* [Mana Advantage]
1x Assassin's Trophy (sld) 139 [Targeted Disruption]
```

### `cubecobra_csv`

[CubeCobra](https://cubecobra.com) CSV export format. Export your cube from CubeCobra using the "Export as CSV" option.

```csv
name,CMC,Type,Color,Set,Collector Number,Rarity,Color Category,status,Finish,maybeboard,image URL,image Back URL,tags,Notes,MTGO ID,Custom
"Lightning Bolt",1,"Instant",R,"leb","162",common,null,Owned,Non-foil,false,,,"","",-1,false
"Death Ward",1,"Instant",W,"leb","18",common,null,Owned,Non-foil,false,"https://i.imgur.com/ytZ2uaY.png",,"","",-1,false
```

### `deckstats`

[Deckstats](https://deckstats.net) format.

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

[Moxfield](https://moxfield.com) format.

```
1 Ainok Bond-Kin (2X2) 5
1 Pegasus Guardian // Rescue the Foal (CLB) 36
2 Witch Enchanter // Witch-Blessed Meadow (MH3) 239

SIDEBOARD:
1 Containment Priest (M21) 13
1 Deafening Silence (MB2) 9
```

### `mpcfill_xml`

[MPCFill](https://mpcfill.com) XML format.

```xml
<order>
    <details>
        <quantity>6</quantity>
        <bracket>18</bracket>
        <stock>(S30) Standard Smooth</stock>
        <foil>false</foil>
    </details>
    <fronts>
        <card>
            <id>1tc4fgHl6ZGYvg_HATosZydWgtHZSg0kc</id>
            <slots>0,5</slots>
            <name>Treasure (Rachta Lin).jpg</name>
            <query>t:treasure</query>
        </card>
        <card>
            <id>1iMS2cqqqfhx7kDrtzYhqrrjKsZyRFPeK</id>
            <slots>1</slots>
            <name>Alrund, God of the Cosmos (Kieran Yanner).jpg</name>
            <query>alrund god of cosmos</query>
        </card>
        <card>
            <id>1Ibb8tpwwPn6nhg0TlMzeaDvcqXPlfmLe</id>
            <slots>2</slots>
            <name>Titania, Voice of Gaea (Borderless Cristi Balanescu).jpg</name>
            <query>titania voice of gaea</query>
        </card>
        <card>
            <id>1ezjK8iXEdNIE_Ks0CpsTdSHfbePvw_dJ</id>
            <slots>3,4</slots>
            <name>Aberrant Researcher.png</name>
            <query>aberrant researcher</query>
        </card>
    </fronts>
    <backs>
        <card>
            <id>1htRd369fxKsPap5RbI7HUOdAL8-Fn6y2</id>
            <slots>1</slots>
            <name>Hakka, Whispering Raven (Kieran Yanner).jpg</name>
            <query>hakka whispering raven</query>
        </card>
        <card>
            <id>1lqUE-pjgjW74Q-vAu9IRLjHYtwa_CnnO</id>
            <slots>2</slots>
            <name>Titania, Gaea Incarnate Top.png</name>
            <query>titania gaea incarnate top</query>
        </card>
        <card>
            <id>1X9bpWccFfqBjNAhp3j8uJf85ihtMabWi</id>
            <slots>3,4</slots>
            <name>Perfected Form.png</name>
            <query>perfected form</query>
        </card>
    </backs>
    <cardback>1LrVX0pUcye9n_0RtaDNVl2xPrQgn7CYf</cardback>
</order>
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

### `scryfall_json`

[Scryfall](https://scryfall.com) JSON format. When the JSON includes `image_uris`, images are fetched directly from those URLs.

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

### `simple`

A list of card names.

```
Isshin, Two Heavens as One
Arid Mesa
Battlefield Forge
Blazemire Verge
Blightstep Pathway
```

### `url`

Instead of providing a decklist file, you can pass a deck URL directly. This format uses the [`mtg_parser`](https://pypi.org/project/mtg-parser/) library to fetch and parse the deck.

Supported sites and URL formats:

| Site | URL Format |
|------|------------|
| [Aetherhub](https://aetherhub.com) | `https://aetherhub.com/Deck/<deck_name>` |
| [Archidekt](https://archidekt.com) | `https://www.archidekt.com/decks/<deck_id>/` |
| [Deckstats](https://deckstats.net) | `https://deckstats.net/decks/<user_id>/<deck_id>` |
| [Moxfield](https://moxfield.com) | `https://www.moxfield.com/decks/<deck_id>` |
| [MTG Goldfish](https://www.mtggoldfish.com) | `https://www.mtggoldfish.com/deck/<deck_id>` |
| [MTGJSON](https://mtgjson.com) | `https://mtgjson.com/api/v5/decks/<deck_name>.json` |
| [Scryfall](https://scryfall.com) | `https://scryfall.com/<user_id>/decks/<deck_id>/` |
| [Tapped Out](https://tappedout.net) | `https://tappedout.net/mtg-decks/<deck_id>/` |
| [TCGPlayer](https://www.tcgplayer.com) | `https://www.tcgplayer.com/content/magic-the-gathering/deck/<deck_name>/<deck_id>` |

Example:

```sh
python plugins/mtg/fetch.py https://www.moxfield.com/decks/example-deck-id url
```
