import json
import os
from enum import Enum
from re import compile
from typing import Callable

from plugins.legend_of_the_five_rings_lcg.emeralddb import fetch_decklist

# "Link (This Version)" permalink copied from a deck page. Older links end in /view.
DECK_URL_PATTERN = compile(r'https?://(?:www\.)?emeralddb\.org/decks/([0-9a-fA-F-]{36})(?:/view)?/?$')

def parse_deck_helper(data: dict, handle_card: Callable) -> None:
    error_lines = []
    index = 0

    pack_ids = data.get('card_pack_ids') or {}

    for card_id, quantity in data.get('cards', {}).items():
        if not isinstance(quantity, int) or quantity <= 0:
            print(f'Skipping: "{card_id}": {quantity}')
            continue

        index += 1
        print(f'Index: {index}, quantity: {quantity}, card id: {card_id}')
        try:
            handle_card(index, card_id, quantity, pack_ids.get(card_id))
        except Exception as e:
            print(f'Error: {e}')
            error_lines.append((card_id, e))

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

# EmeraldDB decklist JSON, as returned by https://www.emeralddb.org/api/decklists/{id}
# {
#   "format": "emerald",
#   "name": "Example",
#   "cards": {
#     "kyuden-hida": 1,
#     "keeper-of-earth": 1,
#     "fine-katana": 3
#   },
#   "card_pack_ids": {
#     "fine-katana": "emerald-core-set"
#   }
# }
def parse_emeralddb_json(deck_text: str, handle_card: Callable) -> None:
    parse_deck_helper(json.loads(deck_text), handle_card)

# EmeraldDB deck URL
#   https://www.emeralddb.org/decks/75ffc2ba-93a2-4551-bab3-2bb12ce015d7
def parse_emeralddb_url(deck_text: str, handle_card: Callable) -> None:
    if os.path.isfile(deck_text):
        with open(deck_text, 'r', encoding='utf-8-sig') as deck_file:
            deck_text = deck_file.read()

    deck_text = deck_text.strip()

    match = DECK_URL_PATTERN.match(deck_text)
    if not match:
        print(f'"{deck_text}" is not a valid EmeraldDB deck URL.')
        return

    parse_deck_helper(fetch_decklist(match.group(1)), handle_card)

class DeckFormat(str, Enum):
    EMERALDDB_JSON = 'emeralddb_json'
    EMERALDDB_URL = 'emeralddb_url'

def parse_deck(deck_text: str, format: DeckFormat, handle_card: Callable) -> None:
    if format == DeckFormat.EMERALDDB_JSON:
        parse_emeralddb_json(deck_text, handle_card)
    elif format == DeckFormat.EMERALDDB_URL:
        parse_emeralddb_url(deck_text, handle_card)
    else:
        raise ValueError('Unrecognized deck format.')
