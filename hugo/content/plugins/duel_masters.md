---
title: 'Duel Masters'
weight: 32
---

This plugin reads a decklist, fetches the card images from the [official Duel Masters card search](https://dm.takaratomy.co.jp/card/), and puts the card images into the proper `game/` directories.

The official card search is Japanese only, so all card images are Japanese.

This plugin supports the `official` and `id` decklist formats. To learn more, see [here](#formats).

## Basic Instructions

Navigate to the root directory as plugins are not meant to be run in the plugins directory.

If you're on macOS or Linux, open **Terminal**. If you're on Windows, open **PowerShell**.

Create and start your virtual Python environment and install Python dependencies if you have not done so already. See [here]({{% ref "../docs/create/#basic-usage" %}}) for more information.

Put your decklist into a text file in `game/decklist`. In this example, the filename is `deck.txt` and the decklist format is the official format (`official`).

Run the script.

```sh
python plugins/duel_masters/fetch.py game/decklist/deck.txt official
```

Now you can create the PDF using [`create_pdf.py`]({{% ref "../docs/create" %}}).

## Double-Sided Cards

Psychic, Dragheart, and other double-sided cards have their front image put in `game/front/` and their back image put in `game/double_sided/`. Twinpact cards are a single image and only go in `game/front/`.

## CLI Options

```
Usage: fetch.py [OPTIONS] DECK_PATH {official|id}

Options:
  --help  Show this message and exit.
```

## Formats

### `official`

The decklist format used by the [official tournament coverage](https://dm.takaratomy.co.jp/coverage/), where each card is a quantity and a card name in `《》` brackets. Copy the decklist from the page. Other lines, such as section headings, are skipped.

Cards are looked up by name, so the newest printing of each card is used.

```
20　クリーチャー
4	《Disコットン＆Disケラサス》
2	《宇宙妖精エリンギ》
2	《切札勝太&カツキング ー熱血の物語ー》
1	《王道の革命 ドギラゴン》
6　ツインパクト
4	《支配の精霊ペルフェクト / ギャラクシー・チャージャー》
2	《音卿の精霊龍 ラフルル・ラブ / 「未来から来る、だからミラクル」》
14　呪文その他
2	《新世界王の権威》
4	《真気楼と誠偽感の決断》
```

### `id`

A quantity and an official card ID. The card ID is the `id` in the card's page URL on the official card search, for example `dm37-030` from `https://dm.takaratomy.co.jp/card/detail/?id=dm37-030`. Use this format to pick a specific printing.

```
4 dm26rp3-001
2 dm24bd5-006
1 dm37-030
```
