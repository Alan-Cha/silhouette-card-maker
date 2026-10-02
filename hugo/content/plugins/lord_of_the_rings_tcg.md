---
title: 'Lord of the Rings TCG'
weight: 87
---

This plugin reads a decklist and puts the card images into the proper `game/` directories.

This plugin is for the Decipher *The Lord of the Rings Trading Card Game*, including the [Players Council](https://lotrtcgpc.net/) sets and errata played on [Gemp](https://play.lotrtcgpc.net/). For the Fantasy Flight living card game, see the [Lord of the Rings: Living Card Game plugin]({{% ref "lotr_lcg" %}}).

This plugin supports the `gemp_id` and `gemp_url` decklist formats. To learn more, see [here](#formats).

Card images come from the [Players Council wiki](https://wiki.lotrtcgpc.net/) and the image overrides Gemp uses for Players Council errata, promos, and sets.

## Basic Instructions

Navigate to the root directory as plugins are not meant to be run in the plugins directory.

If you're on macOS or Linux, open **Terminal**. If you're on Windows, open **PowerShell**.

Create and start your virtual Python environment and install Python dependencies if you have not done so already. See [here]({{% ref "../docs/create/#basic-usage" %}}) for more information.

Put your decklist into a text file in `game/decklist`. In this example, the filename is `deck.txt` and the decklist format is Gemp blueprint IDs (`gemp_id`).

Run the script.

```sh
python plugins/lord_of_the_rings_tcg/fetch.py game/decklist/deck.txt gemp_id
```

Now you can create the PDF using [`create_pdf.py`]({{% ref "../docs/create" %}}).

## CLI Options

```
Usage: fetch.py [OPTIONS] DECK_PATH {gemp_id|gemp_url}

Options:
  --help  Show this message and exit.
```

## Formats

### `gemp_id`

Gemp blueprint IDs (`{set}_{number}`), one per line, with an optional quantity. Foil (`*`) and tengwar (`T`) suffixes use the regular image.

```
1_290
1_2
1_324
2x 2_6
1x 2_121
2 1_51
1 55_8
1 101_1
```

### `gemp_url`

A link to a Gemp deck page, such as a Gemp share link (`https://play.lotrtcgpc.net/share/deck?id=...`) or a tournament deck. The ring-bearer, the One Ring, the adventure deck, and the draw deck are all fetched.

```
https://play.lotrtcgpc.net/gemp-lotr-server/tournament/limited_fotr1790739760824/deck/Wingfoot81/html
```

Gemp deck pages link every card to a wiki image, which does not exist for some errata cards. Use `gemp_id` if a card is reported as missing.
