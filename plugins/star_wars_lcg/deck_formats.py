from enum import Enum
from re import compile
from typing import Callable

from plugins.star_wars_lcg.swlcgdb import fetch_deck

DECK_URL_PATTERN = compile(r'^https?://(?:www\.)?swlcgdb\.com/decks/(\d+)/?$')

def parse_deck_helper(data: dict, handle_card: Callable) -> None:
    error_lines = []

    index = 0
    for card in data.get('cards', []):
        quantity = card.get('quantity', 0)
        if not card.get('id') or not card.get('card_block_id') or quantity < 1:
            print(f'Skipping: "{card.get("name")}"')
            continue

        index = index + 1

        print(f'Index: {index}, quantity: {quantity}, id: {card["id"]}, name: {card["name"]}')
        try:
            handle_card(index, card, quantity)
        except Exception as e:
            print(f'Error: {e}')
            error_lines.append((card['name'], e))

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

# SWLCGDB deck URL
#   https://swlcgdb.com/decks/387
def parse_swlcgdb_url(deck_text: str, handle_card: Callable) -> None:
    deck_text = deck_text.strip()

    match = DECK_URL_PATTERN.match(deck_text)
    if not match:
        print(f'"{deck_text}" is not a valid SWLCGDB deck URL.')
        return

    parse_deck_helper(fetch_deck(match.group(1)), handle_card)

class DeckFormat(str, Enum):
    SWLCGDB_URL = 'swlcgdb_url'

def parse_deck(deck_text: str, format: DeckFormat, handle_card: Callable) -> None:
    if format == DeckFormat.SWLCGDB_URL:
        parse_swlcgdb_url(deck_text, handle_card)
    else:
        raise ValueError('Unrecognized deck format.')
