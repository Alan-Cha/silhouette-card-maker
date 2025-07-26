# Altered Plugin

This plugin reads a decklist from [Ajordat](https://altered.ajordat.com/) and puts the card images into the proper `game/` directories.

This plugin currently only supports the ``Ajordat`` format.

## Instructions

Navigate to the [root directory](../..), as the plugins are not meant to be run in the [plugin directory](.).

Open a terminal on your device in the root directory.

> [!NOTE]
> On Windows, this would be the ``PowerShell`` application, unless you use another terminal of your choice.
>
> On MacOS or Linux, this would be the ``Terminal`` application, unless you use another terminal of your choice.

Create and start your Python virtual environment in the terminal.
```bash
.\venv\Scripts\Activate.ps1
```

> [!WARNING]
> If this fails on Windows due to authorization policy issues, then run the following command to get around it.
> ```bash
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
> ```

Then install the Python dependencies in the Python virtual environment using the following command.
```bash
pip install -r requirements.txt  
```

Put your decklist into a text file within the [decklist directory/folder](../../game/decklist).

Now, you are ready to run the program to generate the images for the deck using the following command.
```bash
python plugins/altered/fetch.py game/decklist/deck.txt ajordat
```

And finally, you can generate the [PDF files](../../README.md#create_pdfpy) for the deck to print so that you can play at the table!

## CLI Options

```
Usage: fetch.py [OPTIONS] DECK_PATH {ajordat}

Options:
  --help  Show this message and exit.
```

## Format

### `ajordat`

The format for ``Ajordat``.

```
1 ALT_COREKS_B_OR_01_C
3 ALT_ALIZE_B_MU_31_R2
2 ALT_ALIZE_B_OR_42_R1
2 ALT_ALIZE_B_OR_44_C
2 ALT_BISE_B_OR_49_C
3 ALT_BISE_B_OR_54_C
3 ALT_BISE_B_OR_59_C
2 ALT_CORE_B_LY_15_R2
2 ALT_CORE_B_OR_08_C
2 ALT_CORE_B_OR_09_C
1 ALT_CORE_B_OR_20_U_7022
2 ALT_CORE_B_OR_30_C
2 ALT_CORE_B_YZ_20_R2
1 ALT_COREKS_B_BR_09_U_4235
3 ALT_COREKS_B_OR_05_R1
2 ALT_COREKS_B_OR_14_C
3 ALT_COREKS_B_OR_16_R1
1 ALT_COREKS_B_OR_18_U_1071
3 ALT_COREKS_B_OR_24_C
```