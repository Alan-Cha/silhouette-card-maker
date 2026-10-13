# Force of Will Plugin

This plugin reads a decklist, automatically fetches card art from the official [Force of Will card search](https://www.fowtcg.com/card_search) and puts them in the proper `game/` directories.

This plugin supports the **Force of Will** plain text decklist format. To learn more, see [here](#formats).

## Basic Instructions

Navigate to the [root directory](../..) as plugins are not meant to be run in the [plugin directory](.).

If you're on macOS or Linux, open **Terminal**. If you're on Windows, open **PowerShell**.

Create and start your virtual Python environment and install Python dependencies if you have not done so already. See [here](../../README.md#basic-usage) for more information.

Put your decklist into a text file in [game/decklist](../game/decklist/). In this example, the filename is `deck.txt` and the decklist format is Force of Will (`fow`).

Run the script.

```sh
python plugins/force_of_will/fetch.py game/decklist/deck.txt fow
```

Now you can create the PDF using [`create_pdf.py`](../../README.md#create_pdfpy).

## CLI Options

```
Usage: fetch.py [OPTIONS] DECK_PATH {fow}

Options:
  --help  Show this message and exit.
```

## Formats

### `fow`

Plain text format, as written on tournament decklists. Each card line is a quantity followed by the card name, optionally with an `x` after the quantity. Section headers such as `Ruler`, `Main Deck`, `Magic Stone Deck`, and `Sideboard` are skipped.

```
Ruler
1 Lehen, Legendary Explorer
Main Deck
4 Group of Explorers
4 Silmeria, Explorer of Ruins
4 Lunya, Master Guide
4 Spirit of the Mirage Ruins
3 Eye Collecting Spirit
3 Water Spirit of the Lamp
2 Sphinx of the Mirage Ruins
2 Guardian Golem of the Ruins
2 Armor of the King of Kings
2 Flowers of the Dream Reign
2 Stallion of the Allfather
2 Statue of the Misty Dragon
4 Cursed Mirror of the Snake
2 Flashfreeze
Magic Stone Deck
2 Epic Stone of the Treasure
2 Fragment of the Emerald Tablet
3 Light Magic Stone
3 Water Magic Stone
```

Cards are looked up by exact name and use the newest set printing on [fowtcg.com](https://www.fowtcg.com/cardlist). The back of a double-sided ruler (its J-ruler or order) is saved to `game/double_sided/`.

The official card search only covers cards from the Duel Cluster onwards and does not yet list every recent product, so older cards and some new cards cannot be found.
