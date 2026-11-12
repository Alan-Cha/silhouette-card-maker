# Gundam M.S. War Plugin

This plugin reads a decklist and puts the card images into the proper `game/` directories.

[Gundam M.S. War](https://gundammswar.fandom.com/wiki/Gundam_M.S_War) is the out-of-print Bandai America trading card game from 2001, based on *Mobile Suit Gundam Wing* (with *Endless Waltz* and *Mobile Suit Gundam* expansions). It is not the 2025 Gundam Card Game; for that, use the [Gundam plugin](../gundam/README.md).

Card images come from the fan-run [Gundam M.S. War wiki](https://gundammswar.fandom.com/wiki/Gundam_M.S_War).

This plugin supports the `text` and `names` decklist formats. To learn more, see [here](#formats).

## Basic Instructions

Navigate to the [root directory](../..) as plugins are not meant to be run in the [plugin directory](.).

If you're on macOS or Linux, open **Terminal**. If you're on Windows, open **PowerShell**.

Create and start your virtual Python environment and install Python dependencies if you have not done so already. See [here](../../README.md#basic-usage) for more information.

Put your decklist into a text file in [game/decklist](../game/decklist/). In this example, the filename is `deck.txt` and the decklist format is `text`.

Run the script.

```sh
python plugins/gundam_ms_war/fetch.py game/decklist/deck.txt text
```

Now you can create the PDF using [`create_pdf.py`](../../README.md#create_pdfpy).

## CLI Options

```
Usage: fetch.py [OPTIONS] DECK_PATH {text|names}

Options:
  --help  Show this message and exit.
```

## Formats

### `text`

One card per line: the quantity (optionally followed by `x`), the card number, and an optional card name. Card numbers are printed on the cards: `MS` (Mobile Suit), `PL` (Pilot), `EV` (Event), and `BF` (Battlefield), with `p` for promos such as `BF-p03`. Lines that don't match are skipped.

```
3 MS-001 Wing Gundam
2 MS-003 Gundam Deathscythe
2x MS-025 Wing Gundam Zero
3 PL-001 Heero Yuy
2 PL-002 Duo Maxwell
2 EV-001 Operation Meteor
1 EV-023 Zero System
1 BF-001 Liberation Army Village
1 BF-p03 New York, NY
```

### `names`

One card per line: the quantity (optionally followed by `x`) and the card name. Names are looked up on the wiki's [Text Check List](https://gundammswar.fandom.com/wiki/Text_Check_List), ignoring case and spacing. Many names are printed on several cards (for example, `Leo` is MS-011, MS-016, MS-042, and six more, and `Heero Yuy` is PL-001, PL-015, and PL-039); such a line is reported as an error that lists the candidate card numbers, so use the `text` format for those cards. Promos are not on the check list, so they also need the `text` format.

```
3 Wing Gundam Zero
2 Gundam Deathscythe Hell
3x Operation Meteor
1 Zero System
1 Liberation Army Village
```

## Card Backs

The plugin only fetches card fronts. Gundam M.S. War cards share one card back, which you provide in `game/back/`. The wiki has no clean scan of it: its [`Missing_back_side.jpg`](https://gundammswar.fandom.com/wiki/File:Missing_back_side.jpg) is the card back overlaid with "MIA" text, used as a placeholder for missing cards.

## Mission Cards

Mission Objective cards have no card numbers, so neither format can fetch them. The wiki has scans of the four from the Wing Gundam Team and OZ Corps starter sets, which you can save into `game/front/` yourself: [Wing_team_missions_01.jpg](https://gundammswar.fandom.com/wiki/File:Wing_team_missions_01.jpg), [Wing_team_missions_02.jpg](https://gundammswar.fandom.com/wiki/File:Wing_team_missions_02.jpg), [Oz_missions_01.jpg](https://gundammswar.fandom.com/wiki/File:Oz_missions_01.jpg), and [Oz_missions_02.jpg](https://gundammswar.fandom.com/wiki/File:Oz_missions_02.jpg). The Earth Federation and Principality of Zeon mission cards are not on the wiki.

## Image Quality

The plugin downloads the original files uploaded to the wiki, which is the largest version available. Most scans are about 510×703 pixels, roughly 200 DPI at card size. A few promos are smaller (for example, BF-p03 is 365×512 and BF-p07 is 150×211), so they print blurrier.
