from re import compile
from enum import Enum
from typing import Callable, Tuple
from api import get_aidalondb_decks

card_data_tuple = Tuple[str, int] # Card ID, Quantity

def parse_deck_helper(deck_text: str, handle_card: Callable, deck_splitter: Callable, is_card_line: Callable[[str], bool], extract_card_data: Callable[[str], card_data_tuple]) -> None:
    error_lines = []

    index = 0
    for line in deck_splitter(deck_text):
        if is_card_line(line):
            index = index + 1

            card_id, quantity = extract_card_data(line)

            print(f'Index: {index}, quantity: {quantity}, card id: {card_id}')
            try:
                handle_card(index, card_id, quantity)
            except Exception as e:
                print(f'Error: {e}')
                error_lines.append((line, e))

        else:
            print(f'Skipping: "{line}"')

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

def parse_aidalondb(deck_text: str, handle_card: Callable) -> None:

    def is_aidalondb_line(line) -> bool:
        return line.get('cardId') and line.get('amount')

    def extract_aidalondb_card_data(line) -> card_data_tuple:
        match = is_aidalondb_line(line)
        if match:
            card_id = line.get('cardId')
            quantity = line.get('amount')

            return (card_id, quantity)

    parse_deck_helper(deck_text, handle_card, get_aidalondb_decks, is_aidalondb_line, extract_aidalondb_card_data)

class DeckFormat(str, Enum):
    AIDALONDB = 'aidalondb'

def parse_deck(deck_text: str, format: DeckFormat, handle_card: Callable) -> None:
    if format == DeckFormat.AIDALONDB:
        return parse_aidalondb(deck_text, handle_card)
    else:
        raise ValueError('Unrecognized deck format.')

if __name__ == '__main__':
    parse_deck()