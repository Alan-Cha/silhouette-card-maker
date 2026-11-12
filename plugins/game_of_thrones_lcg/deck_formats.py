import json
import os
from enum import Enum
from re import compile
from typing import Callable

from plugins.game_of_thrones_lcg.api import fetch_decklist

DECKLIST_URL_PATTERN = compile(r'https?://(?:www\.)?thronesdb\.com/decklist/view/(\d+)')

def parse_deck_helper(slots: dict, handle_card: Callable) -> None:
    error_lines = []
    index = 0

    for code, quantity in slots.items():
        if not isinstance(quantity, int) or quantity < 1:
            print(f'Skipping: "{code}": {quantity}')
            continue

        index += 1

        # No name is available here -- slots are just code/quantity pairs.
        # handle_card (fetch_card_art) logs the full line once it knows the
        # card's name.
        try:
            handle_card(index, code, quantity)
        except Exception as e:
            print(f'Error: {e}')
            error_lines.append((code, e))

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

# ThronesDB public API decklist JSON (https://thronesdb.com/api/public/decklist/<id>)
# The agenda is included in "slots". The faction card is not a database card,
# so it is not printed.
# {
#   "faction_code": "lannister",
#   "slots": {
#     "01003": 1,
#     "01028": 2,
#     "01205": 1
#   },
#   "agendas": ["01205"]
# }
def parse_thronesdb_json(deck_text: str, handle_card: Callable) -> None:
    data = json.loads(deck_text)
    parse_deck_helper(data.get('slots', {}), handle_card)

# ThronesDB published decklist URL format
#   https://thronesdb.com/decklist/view/1
#   https://thronesdb.com/decklist/view/1/secrets-and-schemes-1-core-set-1.0
def parse_thronesdb_url(deck_text: str, handle_card: Callable) -> None:
    if os.path.isfile(deck_text):
        with open(deck_text, 'r', encoding='utf-8-sig') as deck_file:
            deck_text = deck_file.read()

    deck_text = deck_text.strip()

    match = DECKLIST_URL_PATTERN.match(deck_text)
    if not match:
        print(f'"{deck_text}" is not a valid ThronesDB decklist URL.')
        return

    data = fetch_decklist(match.group(1))
    parse_deck_helper(data.get('slots', {}), handle_card)

class DeckFormat(str, Enum):
    THRONESDB_JSON = 'thronesdb_json'
    THRONESDB_URL = 'thronesdb_url'

def parse_deck(deck_text: str, format: DeckFormat, handle_card: Callable) -> None:
    if format == DeckFormat.THRONESDB_JSON:
        parse_thronesdb_json(deck_text, handle_card)
    elif format == DeckFormat.THRONESDB_URL:
        parse_thronesdb_url(deck_text, handle_card)
    else:
        raise ValueError('Unrecognized deck format.')
