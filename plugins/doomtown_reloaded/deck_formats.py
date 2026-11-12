from enum import Enum
from re import compile
from typing import Callable

from plugins.doomtown_reloaded.dtdb import fetch_dtdb_decklist

DECK_URL_PATTERN = compile(r'^https?://dtdb\.co/(?:[a-z]{2}/)?decklist/(\d+)')

def parse_deck_helper(cards: dict, handle_card: Callable) -> None:
    error_lines = []
    index = 0

    for code, quantity in cards.items():
        if not isinstance(quantity, int) or quantity < 1:
            print(f'Skipping: "{code}: {quantity}"')
            continue

        index += 1

        print(f'Index: {index}, quantity: {quantity}, card code: {code}')
        try:
            handle_card(index, code, quantity)
        except Exception as e:
            print(f'Error: {e}')
            error_lines.append((code, e))

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

# dtdb published decklist URL format
#   https://dtdb.co/en/decklist/3803/3-8-10-law-dogs
#
# The decklist API returns every card in the deck, including the outfit,
# legend, and jokers, as {code: quantity}.
def parse_dtdb_url(deck_text: str, handle_card: Callable) -> None:
    deck_text = deck_text.strip()

    match = DECK_URL_PATTERN.match(deck_text)
    if not match:
        print(f'"{deck_text}" is not a valid dtdb decklist URL.')
        return

    data = fetch_dtdb_decklist(match.group(1))
    parse_deck_helper(data.get('cards', {}), handle_card)

class DeckFormat(str, Enum):
    DTDB_URL = 'dtdb_url'

def parse_deck(deck_text: str, format: DeckFormat, handle_card: Callable) -> None:
    if format == DeckFormat.DTDB_URL:
        parse_dtdb_url(deck_text, handle_card)
    else:
        raise ValueError('Unrecognized deck format.')
