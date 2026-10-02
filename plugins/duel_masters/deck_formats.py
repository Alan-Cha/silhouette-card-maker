from re import compile
from enum import Enum
from typing import Callable, Tuple

card_data_tuple = Tuple[str, int, str]  # Card ID, Quantity, Name

def parse_deck_helper(deck_text: str, handle_card: Callable, is_card_line: Callable[[str], bool], extract_card_data: Callable[[str], card_data_tuple]) -> None:
    error_lines = []

    index = 0
    for line in deck_text.strip().split('\n'):
        line = line.strip()
        if is_card_line(line):
            index = index + 1

            card_id, quantity, name = extract_card_data(line)

            parts = [f'Index: {index}', f'quantity: {quantity}']
            if card_id: parts.append(f'card id: {card_id}')
            if name: parts.append(f'name: {name}')
            print(', '.join(parts))
            try:
                handle_card(index, card_id, name, quantity)
            except Exception as e:
                print(f'Error: {e}')
                error_lines.append((line, e))

        else:
            print(f'Skipping: "{line}"')

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

def parse_official(deck_text: str, handle_card: Callable) -> None:
    pattern = compile(r'^(\d+)\s+《(.+)》$')  # '{Quantity} 《{Name}》'

    def is_official_line(line) -> bool:
        return bool(pattern.match(line))

    def extract_official_card_data(line) -> card_data_tuple:
        match = pattern.match(line)
        if match:
            quantity = int(match.group(1))
            name = match.group(2).strip()
            return ('', quantity, name)

    parse_deck_helper(deck_text, handle_card, is_official_line, extract_official_card_data)

def parse_id(deck_text: str, handle_card: Callable) -> None:
    pattern = compile(r'^(\d+)\s+([A-Za-z0-9]+-[A-Za-z0-9]+)$')  # '{Quantity} {Card ID}'

    def is_id_line(line) -> bool:
        return bool(pattern.match(line))

    def extract_id_card_data(line) -> card_data_tuple:
        match = pattern.match(line)
        if match:
            quantity = int(match.group(1))
            card_id = match.group(2)
            return (card_id, quantity, '')

    parse_deck_helper(deck_text, handle_card, is_id_line, extract_id_card_data)

class DeckFormat(str, Enum):
    OFFICIAL = 'official'
    ID = 'id'

def parse_deck(deck_text: str, format: DeckFormat, handle_card: Callable) -> None:
    if format == DeckFormat.OFFICIAL:
        return parse_official(deck_text, handle_card)
    elif format == DeckFormat.ID:
        return parse_id(deck_text, handle_card)
    else:
        raise ValueError('Unrecognized deck format.')
