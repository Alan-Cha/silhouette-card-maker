# Riftbound Plugin

This plugin reads a decklist, fetches the card image from either [Piltover Archive](https://piltoverarchive.com/) or [Riftmana](https://riftmana.com/), and puts the card images into the proper `game/` directories.

This plugin currently supports the ``TTS (Tabletop Simulator)`` and ``Pixelborn`` formats.

> [!WARNING]
> ``Pixelborn`` will be shutdown August 7th, 2025 with Riot's announcement of their [Digital Tools Policy for Riftbound](https://developer.riotgames.com/docs/riftbound). As a result, the format itself may not receive any more attention. However, the ``Pixelborn`` format will remain here, in the event that it still persists beyond that date.

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

Now, you are ready to run the program to generate the images for the deck.

If your deck is in the ``TTS`` format, then use one of the following commands.

> [!NOTE]
> If you want to use [Piltover Archive](https://piltoverarchive.com/) for images, then use the following command.
> ```bash
> python plugins/riftbound/fetch.py game/decklist/deck.txt tts piltover_archive
> ```
> If you want to use [Riftmana](https://riftmana.com/) for images, then use the following command.
> ```bash
> python plugins/riftbound/fetch.py game/decklist/deck.txt tts riftmana
> ```

If your deck is in the ``Pixelborn`` format, then use one of the following commands.

> [!NOTE]
> If you want to use [Piltover Archive](https://piltoverarchive.com/) for images, then use the following command.
> ```bash
> python plugins/riftbound/fetch.py game/decklist/deck.txt pixelborn piltover_archive
> ```
> If you want to use [Riftmana](https://riftmana.com/) for images, then use the following command.
> ```bash
> python plugins/riftbound/fetch.py game/decklist/deck.txt pixelborn riftmana
> ```

And finally, you can generate the [PDF files](../../README.md#create_pdfpy) for the deck to print so that you can play at the table!

## CLI Options

```
Usage: fetch.py [OPTIONS] DECK_PATH {tts|pixelborn}
                {piltover_archive|riftmana}

Options:
  --help  Show this message and exit.
```

## Formats

### `tts`

The format for ``TTS``.

```
OGN-265-1 OGN-246-1 OGN-245-1 OGN-245-1 OGN-245-1 OGN-095-1 OGN-095-1 OGN-095-1 OGN-213-1 OGN-213-1 OGN-213-1 OGN-266-1 OGN-266-1 OGN-266-1 OGN-216-1 OGN-216-1 OGN-216-1 OGN-209-1 OGN-209-1 OGN-209-1 OGN-096-1 OGN-096-1 OGN-096-1 OGN-211-1 OGN-211-1 OGN-211-1 OGN-218-1 OGN-218-1 OGN-218-1 OGN-208-1 OGN-208-1 OGN-208-1 OGN-239-1 OGN-239-1 OGN-239-1 OGN-233-1 OGN-233-1 OGN-233-1 OGN-234-1 OGN-234-1 OGN-234-1 OGN-289-1 OGN-294-1 OGN-284-1 OGN-214-1 OGN-214-1 OGN-214-1 OGN-214-1 OGN-214-1 OGN-214-1 OGN-214-1 OGN-214-1 OGN-214-1 OGN-214-1 OGN-214-1 OGN-214-1
```

### `pixelborn`

The format for ``Pixelborn``.

```
T0dOLTI2NS0xJE9HTi0yNDYtMSRPR04tMjQ1LTEkT0dOLTI0NS0xJE9HTi0yNDUtMSRPR04tMDk1LTEkT0dOLTA5NS0xJE9HTi0wOTUtMSRPR04tMjEzLTEkT0dOLTIxMy0xJE9HTi0yMTMtMSRPR04tMjY2LTEkT0dOLTI2Ni0xJE9HTi0yNjYtMSRPR04tMjE2LTEkT0dOLTIxNi0xJE9HTi0yMTYtMSRPR04tMjA5LTEkT0dOLTIwOS0xJE9HTi0yMDktMSRPR04tMDk2LTEkT0dOLTA5Ni0xJE9HTi0wOTYtMSRPR04tMjExLTEkT0dOLTIxMS0xJE9HTi0yMTEtMSRPR04tMjE4LTEkT0dOLTIxOC0xJE9HTi0yMTgtMSRPR04tMjA4LTEkT0dOLTIwOC0xJE9HTi0yMDgtMSRPR04tMjM5LTEkT0dOLTIzOS0xJE9HTi0yMzktMSRPR04tMjMzLTEkT0dOLTIzMy0xJE9HTi0yMzMtMSRPR04tMjM0LTEkT0dOLTIzNC0xJE9HTi0yMzQtMSRPR04tMjg5LTEkT0dOLTI5NC0xJE9HTi0yODQtMSRPR04tMjE0LTEkT0dOLTIxNC0xJE9HTi0yMTQtMSRPR04tMjE0LTEkT0dOLTIxNC0xJE9HTi0yMTQtMSRPR04tMjE0LTEkT0dOLTIxNC0xJE9HTi0yMTQtMSRPR04tMjE0LTEkT0dOLTIxNC0xJE9HTi0yMTQtMQ==
```