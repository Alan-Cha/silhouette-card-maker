# Pokemon Plugin

This plugin reads a decklist and automatically fetches the card art and puts them in the proper `game/` directories.

## Basic instructions

Navigate to the [root directory](../..). This plugin is not meant to be run in `plugins/mtg/`.

If you're on macOS or Linux, open **Terminal**. If you're on Windows, open **PowerShell**.

Create and start your virtual Python environment and install Python dependencies if you have not done so already. See [here](../../README.md#basic-instructions) for more information.

Put your decklist into a text file in `game/decklist`. In this example, the filename is `deck.txt` and the decklist format is Limitless (`limitless`).

Run the script.

```sh
python plugins/pokemon/fetch.py game/decklist/deck.txt limitless
```

Now you can create the PDF using [`create_pdf.py`](../../README.md#create_pdf.py).