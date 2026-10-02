---
title: 'Bushiroad'
weight: 27
---

This plugin reads deck codes, automatically retrieves the decklist and fetches card art from Bushiroad, and puts them in the proper `game/` directories.

This plugin supports decklist exports from [Bushiroad Deck Log](https://decklog-en.bushiroad.com/) and [Bushiroad Deck Log (Japanese)](https://decklog.bushiroad.com/) for Cardfight Vanguard, Shadowverse: Evolve, Weiss Schwarz, Godzilla, and hololive. To learn more, see [here](#formats).

## Basic Instructions

Navigate to the root directory as plugins are not meant to be run in the plugins directory.

If you're on macOS or Linux, open **Terminal**. If you're on Windows, open **PowerShell**.

Create and start your virtual Python environment and install Python dependencies if you have not done so already. See [here]({{% ref "../docs/create/#basic-usage" %}}) for more information.

Put your decklist into a text file in `game/decklist`. In this example, the filename is `deck.txt` and the decklist format is Bushiroad Deck Log (`bushiroad`).

Run the script.

```sh
python plugins/bushiroad/fetch.py game/decklist/deck.txt bushiroad_url
```

Now you can create the PDF using [`create_pdf.py`]({{% ref "../docs/create" %}}).

## CLI Options

```
Usage: fetch.py [OPTIONS] DECK_PATH {bushiroad_url}

Options:
  --help  Show this message and exit.
```

## Formats

### `bushiroad_url`

Bushiroad Deck Log URL format.

```
https://decklog-en.bushiroad.com/view/1HF6L
```

Japanese Deck Log URLs are also supported. Note that the same deck code refers to different decks on the English and Japanese sites, so use the full URL. Bare deck codes are skipped rather than guessed.

```
https://decklog.bushiroad.com/view/1HF6L
```

Japanese card names have no Latin characters, so image filenames use the card number instead (for example, `1V-SS100291.png`).

You can also use a Bushiroad Deck Log URL directly in the command line.

```sh
python plugins/bushiroad/fetch.py https://decklog-en.bushiroad.com/view/5ZJ74 bushiroad_url
```