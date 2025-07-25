# Pokemon Plugin

This plugin extracts images from a PDF generated from [LimitlessTCG's proxy generator](https://limitlesstcg.com/tools/proxies) puts them in the proper `game/` directories.

## Basic instructions

Create a PDF of cards using [LimitlessTCG's proxy generator](https://limitlesstcg.com/tools/proxies).

Navigate to the [root directory](../..). This plugin is not meant to be run in `plugins/pokemon/`.

If you're on macOS or Linux, open **Terminal**. If you're on Windows, open **PowerShell**.

Create and start your virtual Python environment and install Python dependencies if you have not done so already. See [here](../../README.md#basic-instructions) for more information.

Put your decklist PDF file in `game/decklist`. In this example, the filename is `deck.pdf`.

Run the script

```sh
python pdf_extractor.py game/decklist/deck.pdf game/front
```

Now you can create the Cameo cutting PDF using [`create_pdf.py`](../../README.md#create_pdf.py).