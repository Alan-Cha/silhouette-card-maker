import os
from enum import Enum
from re import compile
from typing import Callable

from plugins.warhammer_40k_conquest.conquestdb import fetch_deck_text

CARD_LINE_PATTERN = compile(r'^(\d+)x\s+(.+)$') # '{quantity}x {name}'
SEPARATOR_PATTERN = compile(r'^-{3,}$')
DECK_URL_PATTERN = compile(r'https?://(?:www\.)?conquestdb\.com/decks/([^/\s]+)/([^/\s]+)/?$')

# ConquestDB "Download Deck" format
#   Square root of 7 kyubed
#   ----------------------------------------------------------------------
#   Grigory Maksim
#   Astra Militarum
#   ----------------------------------------------------------------------
#   Signature Squad
#
#   4x Maksim's Squadron
#   1x Clearing the Path
#   ...
#
# The warlord is the first line after the first separator, before any card line. Every other card is a '{quantity}x {name}' line,
# so a plain list of '{quantity}x {name}' lines works too.
def parse_conquestdb(deck_text: str, handle_card: Callable) -> None:
    error_lines = []
    index = 0
    separators = 0
    expect_warlord = False

    for line in deck_text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue

        if SEPARATOR_PATTERN.match(line):
            separators += 1
            expect_warlord = separators == 1 and index == 0
            continue

        match = CARD_LINE_PATTERN.match(line)
        if match:
            quantity = int(match.group(1))
            name = match.group(2).strip()
            warlord = False
        elif expect_warlord:
            quantity = 1
            name = line
            warlord = True
        else:
            print(f'Skipping: "{line}"')
            expect_warlord = False
            continue

        expect_warlord = False
        index += 1

        print(f'Index: {index}, quantity: {quantity}, name: {name}' + (' (warlord)' if warlord else ''))
        try:
            handle_card(index, name, quantity, warlord)
        except Exception as e:
            print(f'Error: {e}')
            error_lines.append((line, e))

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

# ConquestDB URL format
#   https://www.conquestdb.com/decks/Echo/Zq99g5gmBTdfq8cg/
def parse_conquestdb_url(deck_text: str, handle_card: Callable) -> None:
    if os.path.isfile(deck_text):
        with open(deck_text, 'r', encoding='utf-8-sig') as deck_file:
            deck_text = deck_file.read()

    deck_text = deck_text.strip()

    match = DECK_URL_PATTERN.match(deck_text)
    if not match:
        print(f'"{deck_text}" is not a valid ConquestDB deck URL.')
        return

    parse_conquestdb(fetch_deck_text(match.group(1), match.group(2)), handle_card)

class DeckFormat(str, Enum):
    CONQUESTDB = 'conquestdb'
    CONQUESTDB_URL = 'conquestdb_url'

def parse_deck(deck_text: str, format: DeckFormat, handle_card: Callable) -> None:
    if format == DeckFormat.CONQUESTDB:
        parse_conquestdb(deck_text, handle_card)
    elif format == DeckFormat.CONQUESTDB_URL:
        parse_conquestdb_url(deck_text, handle_card)
    else:
        raise ValueError('Unrecognized deck format.')
