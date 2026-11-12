---
title: 'Silhouette Card Maker'
cascade:
  type: docs
---

![](/images/scm_banner.png)

Ever wanted to make your own custom card game but without the hassle of a craft knife, a rotary cutter, or a paper guillotine? How about making your own proxies to playtest your favorite TCG?

You can do it all with the press of a button and a cutting machine! And I can show you how!

If this is your first time here, check out the [tutorial](tutorial/)! Please join our [Discord server](https://discord.gg/jhsKmAgbXc) too!

## Demo

Watch me cut **104 cards in 26 minutes** without breaking a sweat!

{{< youtube RVHtqsRW8t8 >}}

## Purpose

The purpose of this repo is to enable you to use a Silhouette cutting machine to create card games and proxies. Proxies are only intended to be used for casual play and playtesting.

Proxies should be easily identifiable as proxies. You may not use this repo to create counterfeit cards to deceive people or to play in sanctioned tournaments. You are only permitted to sell cards if you are the full privileged copyright holder.

## Contents

* [code repository](https://github.com/Alan-Cha/silhouette-card-maker)
* [tutorial](tutorial/)
* [supply list](tutorial/supplies)
* [create_pdf.py](docs/create), a script for laying out your cards in a PDF
* [offset_pdf.py](docs/offset), a script for adding an offset to your PDF
* [cutting_templates/](https://github.com/Alan-Cha/silhouette-card-maker/tree/main/cutting_templates), a directory containing Silhouette Studio cutting templates
* [calibration/](https://github.com/Alan-Cha/silhouette-card-maker/tree/main/calibration), a directory containing offset calibration sheets
* [examples/](https://github.com/Alan-Cha/silhouette-card-maker/tree/main/examples), a directory containing sample games
* [plugins/](plugins/), a directory containing scripts for streamlining card image acquisition

## Supported Sizes

The most common card sizes for games are:
* `standard`, for standard TCG cards
* `poker`
* `bridge`

Other notable card sizes include:
* `business`
* `euro_business`
* `credit`
* `photo`, for K-pop photocards
* `poker_chip`, for poker chips and round board game tokens (see [Circular Cards](#circular-cards))

The table below shows all possible paper and card size combinations and the layout of the cards. Rows are grouped by shape: rectangular, then square, then circular.

| Format | `letter` | `legal` | `tabloid` | `a4` | `a3` | `arch_b` |
|---|---|---|---|---|---|---|
| `standard` | 4x2 (8) | 5x2 (10) | 4x4 (16) | 4x2 (8) | 6x3 (18) | 6x3 (18) |
| `poker` | 4x2 (8) | 5x2 (10) | 4x4 (16) | 4x2 (8) | 4x4 (16) | 6x3 (18) |
| `bridge` | 4x2 (8) | 5x2 (10) | 4x4 (16) | 3x3 (9) | 6x3 (18) | 7x3 (21) |
| `american_mini` | 4x4 (16) | 7x3 (21) | 9x4 (36) | 4x4 (16) | 9x4 (36) | 10x4 (40) |
| `business` | 2x5 (10) | 2x6 (12) | 4x5 (20) | 2x5 (10) | 3x7 (21) | 3x8 (24) |
| `catan` | 3x3 (9) | 6x2 (12) | 7x3 (21) | 5x2 (10) | 7x3 (21) | 5x5 (25) |
| `credit` | 2x4 (8) | 2x6 (12) | 4x4 (16) | 2x5 (10) | 3x7 (21) | 3x7 (21) |
| `domino` | 5x2 (10) | 7x2 (14) | 5x4 (20) | 5x2 (10) | 8x3 (24) | 9x3 (27) |
| `euro_business` | 3x3 (9) | 2x5 (10) | 3x7 (21) | 3x3 (9) | 3x7 (21) | 3x7 (21) |
| `euro_mini` | 4x3 (12) | 4x4 (16) | 9x3 (27) | 6x2 (12) | 8x4 (32) | 9x4 (36) |
| `japanese` | 4x2 (8) | 5x2 (10) | 4x4 (16) | 3x3 (9) | 6x3 (18) | 7x3 (21) |
| `jumbo` | 2x1 (2) | 2x2 (4) | 4x1 (4) | 3x1 (3) | 3x2 (6) | 3x3 (9) |
| `micro` | 7x4 (28) | 9x4 (36) | 7x9 (63) | 5x6 (30) | 11x6 (66) | 12x6 (72) |
| `mini` | 5x3 (15) | 7x3 (21) | 8x4 (32) | 4x4 (16) | 8x4 (32) | 9x4 (36) |
| `standard_double` | 2x2 (4) | 2x2 (4) | 4x2 (8) | 2x2 (4) | 3x3 (9) | 3x3 (9) |
| `tarot` | 2x2 (4) | 4x1 (4) | 5x2 (10) | 2x2 (4) | 5x2 (10) | 4x3 (12) |
| `bridge_square` | 3x4 (12) | 5x3 (15) | 4x7 (28) | 3x4 (12) | 4x6 (24) | 4x7 (28) |
| `domino_square` | 4x5 (20) | 7x4 (28) | 5x9 (45) | 4x5 (20) | 6x8 (48) | 6x9 (54) |
| `70mm_square` | 3x2 (6) | 4x2 (8) | 5x3 (15) | 3x2 (6) | 5x3 (15) | 5x4 (20) |
| `40mm_circle` | 4x6 (24) | 4x8 (32) | 6x9 (54) | 4x6 (24) | 6x9 (54) | 6x10 (60) |
| `39mm_circle` | 4x6 (24) | 4x8 (32) | 6x10 (60) | 4x6 (24) | 6x9 (54) | 7x10 (70) |
| `30mm_circle` | 6x7 (42) | 6x10 (60) | 8x12 (96) | 6x8 (48) | 8x12 (96) | 9x13 (117) |
| `1in_circle` | 7x9 (63) | 7x12 (84) | 9x15 (135) | 7x9 (63) | 10x14 (140) | 10x16 (160) |
| `25mm_circle` | 7x9 (63) | 7x12 (84) | 9x15 (135) | 7x10 (70) | 10x15 (150) | 10x16 (160) |
| `20mm_circle` | 9x11 (99) | 9x15 (135) | 12x18 (216) | 9x12 (108) | 13x18 (234) | 13x19 (247) |

The tables below show each card size, sorted by size and grouped by shape.

### Rectangular Cards

| Card size | Inches | Millimeters | Ratio | Notes |
| --- | --- | --- | --- | --- |
| `jumbo` | **3.5 x 5.5** | 88.9 x 139.7 | 0.6364 |  |
| `standard_double` | 3.465 x 4.961 | **88 x 126** | 0.6984 | Magic: The Gathering oversized <ul><li>Planechase</li> <li>Archenemy</li> <li>Commander</li></ul> |
| `tarot` | **2.75 x 4.75** | 69.85 x 120.65 | 0.5789 |  |
| `poker` | **2.5 x 3.5** | 63.5 x 88.9 | 0.7143 |  |
| `bridge` | **2.25 x 3.5** | 57.15 x 88.9 | 0.6429 |  |
| `business` | **2 x 3.5** | 50.8 x 88.9 | 0.5714 | Business cards |
| `domino` | **1.75 x 3.5** | 44.45 x 88.9 | 0.5000 |  |
| `standard` | 2.48 x 3.465 | **63 x 88** | 0.7159 | AKA `euro_poker`<br>Most standard TCGs<ul><li>**Magic: The Gathering**</li><li>**Pokémon**</li><li>**Lorcana**</li><li>**One Piece**</li><li>**Riftbound**</li></ul> |
| `japanese` | 2.323 x 3.386 | **59 x 86** | 0.6860 |  |
| `credit` | **2.125 x 3.375** | 53.975 x 85.725 | 0.6296 | Credit cards <ul><li>CR80</li><li>ISO/IEC 7810</li></ul> |
| `euro_business` | 2.165 x 3.346 | **55 x 85** | 0.6471 | AKA `photo`<br>EU business cards<br>K-pop photocards |
| `catan` | 2.126 x 3.15 | **54 x 80** | 0.6750 |  |
| `euro_mini` | 1.732 x 2.677 | **44 x 68** | 0.6471 | AKA `mini_euro` |
| `mini` | **1.75 x 2.5** | 44.45 x 63.5 | 0.7000 |  |
| `american_mini` | 1.614 x 2.48 | **41 x 63** | 0.6508 | AKA `mini_american` |
| `micro` | **1.25 x 1.75** | 31.75 x 44.45 | 0.7143 |  |

### Square Cards

| Card size | Inches | Millimeters | Notes |
| --- | --- | --- | --- |
| `70mm_square` | 2.756 | **70** |  |
| `bridge_square` | **2.25** | 57.15 |  |
| `domino_square` | **1.75** | 44.45 |  |

### Circular Cards

| Card size | Inches (⌀) | Millimeters (⌀) | Notes |
| --- | --- | --- | --- |
| `40mm_circle` | 1.575 | **40** | "Silver dollar" size for oversized board game tokens; close to many home-set poker chips |
| `39mm_circle` | 1.535 | **39** | AKA `poker_chip`<br>Standard casino/clay poker chip diameter |
| `30mm_circle` | 1.181 | **30** | Board game tokens<br>e.g. Scythe's $20 coin |
| `1in_circle` | **1** | 25.4 | Generic 1-inch counters and chips |
| `25mm_circle` | 0.984 | **25** | Board game tokens<br>e.g. Chaos in the Old World's tokens |
| `20mm_circle` | 0.787 | **20** | Board game tokens<br>e.g. Scythe's $1 coin |

The table below shows each paper size, sorted by size and standard.

| Paper size | Inches | Millimeters | Notes |
| --- | --- | --- | --- |
| `letter` | **8.5 x 11** | 215.9 x 279.4 | AKA `ansi_a` |
| `legal` | **8.5 x 14** | 215.9 x 355.6 |  |
| `tabloid` | **11 x 17** | 279.4 x 431.8 | AKA `ansi_b` |
| `a4` | 8.268 x 11.693 | **210 x 297** |  |
| `a3` | 11.693 x 16.535 | **297 x 420** |  |
| `arch_b` | **12 x 18** | 304.8 x 457.2 |  |