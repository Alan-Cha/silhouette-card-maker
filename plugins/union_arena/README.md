# Union Arena Plugin

This plugin reads a decklist and puts the card images into the proper `game/` directories.

This plugin supports the `exburst` and `text` decklist formats. To learn more, see [here](#formats).

## Basic Instructions

Navigate to the [root directory](../..) as plugins are not meant to be run in the [plugin directory](.).

If you're on macOS or Linux, open **Terminal**. If you're on Windows, open **PowerShell**.

Create and start your virtual Python environment and install Python dependencies if you have not done so already. See [here](../../README.md#basic-usage) for more information.

Put your decklist into a text file in [game/decklist](../game/decklist/). In this example, the filename is `deck.txt` and the decklist format is ExBurst (`exburst`).

Run the script.

```sh
python plugins/union_arena/fetch.py game/decklist/deck.txt exburst
```

Now you can create the PDF using [`create_pdf.py`](../../README.md#create_pdfpy).

## CLI Options

```
Usage: fetch.py [OPTIONS] DECK_PATH {exburst|text}

Options:
  --help  Show this message and exit.
```

## Formats

Card numbers use the official format printed on the card and shown on the [official card list](https://www.unionarena-tcg.com/na/cardlist/), such as `UE03BT/JJK-1-001` or `UEPR/JJK-1-001`. The set prefix (`UE03BT/`) is required; short numbers such as `JJK-1-001` are reported as errors because the same number is printed in several sets. Parallel (alternate art) cards can be requested by adding the official `_p1` suffix, such as `UE03BT/JJK-1-005_p1`, or ExBurst's `-ALT1` suffix, such as `UE03BT/JJK-1-005-ALT1`.

Card images are downloaded from the official English (North America) card list for `UE` cards, and from the official Asia English card list for Asia cards (such as `UA53BT/CSM-1-001`), falling back to the Japanese card list.

### `exburst`

[ExBurst](https://exburst.dev/ua/en/) format.

```
4 x UE03BT/JJK-1-001
4 x UE03BT/JJK-1-002
2 x UE03BT/JJK-1-005-ALT1
```

### `text`

Plain text format. The card name is optional.

```
4 UE03BT/JJK-1-001 Yuji Itadori
4 UE03BT/JJK-1-002
2 UE03BT/JJK-1-005_p1
```
