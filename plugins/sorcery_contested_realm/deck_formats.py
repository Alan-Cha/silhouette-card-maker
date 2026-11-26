from enum import Enum
from typing import Callable, Tuple
from re import compile
import os
from plugins.sorcery_contested_realm.curiosa import get_curiosa_decklist

card_data_tuple = Tuple[str, int, str, bool] # Name, Quantity, Image URL, Is Site

def parse_deck_helper(deck_text: str, handle_card: Callable, deck_splitter: Callable, is_card_line: Callable[[str], bool], extract_card_data: Callable[[str], card_data_tuple]) -> None:
    error_lines = []

    index = 0
    for line in deck_splitter(deck_text):
        if is_card_line(line):
            index = index + 1

            name, quantity, image_url, is_site = extract_card_data(line)

            print(f'Index: {index}, quantity: {quantity}, name: {name}')
            try:
                handle_card(index, name, image_url, quantity, is_site)
            except Exception as e:
                print(f'Error: {e}')
                error_lines.append((line, e))

        else:
            print(f'Skipping: "{line}"')

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

def parse_curiosa(deck_text: str, handle_card: Callable) -> None:
    # Curiosa moved to sorcerytcg.com and kept its deck IDs, so accept both URLs
    SHARE_URL_PATTERN = compile(r'https://(?:www\.)?(?:curiosa\.io|sorcerytcg\.com)/decks/(\w+)')

    if os.path.isfile(deck_text):
        deck_text = open(deck_text, "r").read()

    for line in deck_text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue

        match = SHARE_URL_PATTERN.match(line)
        if not match:
            print(f'Skipping: "{line}"')
            continue

        deck_id = match.group(1)

        def split_curiosa_deck(_deck_id: str):
            return get_curiosa_decklist(_deck_id)

        def is_curiosa_line(line) -> bool:
            if line.get('card', {}).get('name') and line.get('quantity'):
                return True
            return False

        def extract_curiosa_card_data(line) -> card_data_tuple:
            match = is_curiosa_line(line)
            if match:
                card = line.get('card', {})
                card_name = card.get('name')
                quantity = line.get('quantity')
                printing_id = line.get('printingId')
                printings = card.get('printings', [])
                card_image = next(
                    (printing.get('meta', {}).get('image') for printing in printings if printing.get('id') == printing_id),
                    printings[0].get('meta', {}).get('image') if printings else None
                )
                is_site = card.get('engine', {}).get('type') == 'Site'

                return (card_name, quantity, card_image, is_site)

        parse_deck_helper(deck_id, handle_card, split_curiosa_deck, is_curiosa_line, extract_curiosa_card_data)

class DeckFormat(str, Enum):
    CURIOSA_URL = 'curiosa_url'

def parse_deck(deck_text: str, format: DeckFormat, handle_card: Callable) -> None:
    if format == DeckFormat.CURIOSA_URL:
        return parse_curiosa(deck_text, handle_card)
    else:
        raise ValueError('Unrecognized deck format.')

