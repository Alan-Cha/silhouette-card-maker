import json
import os
from enum import Enum
from re import compile
from typing import Callable

from plugins.marvel_champions.api import fetch_marvelcdb_deck

DECK_URL_PATTERN = compile(r'https?://(?:www\.)?marvelcdb\.com/(deck|decklist)/view/(\d+)')

def handle_slots(data: dict, handle_card: Callable) -> None:
    error_lines = []
    index = 0

    slots = dict(data.get('slots', {}))

    hero_code = data.get('hero_code')
    if hero_code:
        slots[hero_code] = slots.get(hero_code, 0) + 1

    for code, quantity in slots.items():
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

# MarvelCDB deck JSON (as returned by the MarvelCDB public API)
# {
#   "hero_code": "01001a",
#   "slots": {
#     "01002": 1,
#     "01003": 1,
#     "01074": 2
#   }
# }
def parse_marvelcdb_json(deck_text: str, handle_card: Callable) -> None:
    data = json.loads(deck_text)
    handle_slots(data, handle_card)

# MarvelCDB URL format
#   https://marvelcdb.com/deck/view/12345
#   https://marvelcdb.com/decklist/view/12345/deck-name-1.0
def parse_marvelcdb_url(deck_text: str, handle_card: Callable) -> None:
    if os.path.isfile(deck_text):
        with open(deck_text, 'r') as deck_file:
            deck_text = deck_file.read()

    deck_text = deck_text.strip()

    match = DECK_URL_PATTERN.match(deck_text)
    if not match:
        print(f'"{deck_text}" is not a valid MarvelCDB deck URL.')
        return

    is_decklist = match.group(1) == 'decklist'
    deck_id = match.group(2)

    data = fetch_marvelcdb_deck(deck_id, is_decklist)
    handle_slots(data, handle_card)

class DeckFormat(str, Enum):
    MARVELCDB_JSON = 'marvelcdb_json'
    MARVELCDB_URL = 'marvelcdb_url'

def parse_deck(deck_text: str, format: DeckFormat, handle_card: Callable) -> None:
    if format == DeckFormat.MARVELCDB_JSON:
        parse_marvelcdb_json(deck_text, handle_card)
    elif format == DeckFormat.MARVELCDB_URL:
        parse_marvelcdb_url(deck_text, handle_card)
    else:
        raise ValueError('Unrecognized deck format.')
