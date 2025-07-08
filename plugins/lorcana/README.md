# Lorcana Plugin

This plugin reads a decklist, automatically fetches  card art from [Lorcast](https://lorcast.com) and puts them in the proper `game/` directories.

This plugin supports decklist exports from [Dreamborn.ink](https://dreamborn.ink). To learn more, see [here](#formats).

## Basic instructions

Navigate to the [root directory](../..). This plugin is not meant to be run in `plugins/lorcana/`.

If you're on macOS or Linux, open **Terminal**. If you're on Windows, open **PowerShell**.

Create and start your virtual Python environment and install Python dependencies if you have not done so already. See [here](../../README.md#basic-instructions) for more information.

Put your decklist into a text file in `game/decklist`. In this example, the filename is `deck.txt` and the decklist format is Dreamborn (`dreamborn`).

Run the script.

```shell
python plugins/lorcana/fetch.py game/decklist/deck.txt dreamborn
```

Now you can create the PDF using [`create_pdf.py`](../../README.md#create_pdfpy).

## Format

### Structure

`dreamborn`: Decks are saved as plain text files (`.txt`) in either of the following formats:

```
[quantity] [card name] - [card version] [enchanted]       
[quantity] [card name], [card version] [enchanted]
```

### Enchanted Artwork

Dreamborn does not natively have a way to select the Enchanted artwork for cards. This feature has been included here by adding `*E*` after the card version.

### Example

```
1 Elsa, Spirit of Winter *E*
4 Magic Broom, Illuminary Keeper
4 Diablo - Obedient Raven
4 Mr. Smee, Bumbling Mate
1 Anna - True-Hearted *E*
4 Pete - Games Referee
4 Merlin, Goat
```