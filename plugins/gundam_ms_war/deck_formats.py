from re import compile, IGNORECASE
from enum import Enum
from typing import Callable, Tuple

card_data_tuple = Tuple[str, int, str]  # Card Number, Quantity, Name

def parse_deck_helper(deck_text: str, handle_card: Callable, is_card_line: Callable[[str], bool], extract_card_data: Callable[[str], card_data_tuple]) -> None:
    error_lines = []

    index = 0
    for line in deck_text.strip().split('\n'):
        if is_card_line(line):
            index = index + 1

            card_number, quantity, name = extract_card_data(line)

            parts = [f'Index: {index}', f'quantity: {quantity}', f'card number: {card_number}']
            if name: parts.append(f'name: {name}')
            print(', '.join(parts))
            try:
                handle_card(index, card_number, quantity)
            except Exception as e:
                print(f'Error: {e}')
                error_lines.append((line, e))

        else:
            print(f'Skipping: "{line}"')

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

def parse_text(deck_text: str, handle_card: Callable) -> None:
    # '{Quantity}[x] {Card Number} [{Name}]', e.g. '3 MS-001 Wing Gundam', '2x PL-001', '1 BF-p03'
    pattern = compile(r'^\s*(\d+)\s*x?\s+((?:MS|PL|EV|BF)[-_]?P?\d+)\b\s*(.*)$', IGNORECASE)

    def is_text_line(line) -> bool:
        return bool(pattern.match(line))

    def extract_text_card_data(line) -> card_data_tuple:
        match = pattern.match(line)
        return (match.group(2), int(match.group(1)), match.group(3).strip())

    parse_deck_helper(deck_text, handle_card, is_text_line, extract_text_card_data)

def parse_names(deck_text: str, handle_card: Callable) -> None:
    # '{Quantity}[x] {Name}', e.g. '3 Wing Gundam', '2x Zero System'. handle_card receives the name in place of a card number.
    pattern = compile(r'^\s*(\d+)\s*x?\s+(\S.*?)\s*$', IGNORECASE)

    def is_names_line(line) -> bool:
        return bool(pattern.match(line))

    def extract_names_card_data(line) -> card_data_tuple:
        match = pattern.match(line)
        return (match.group(2), int(match.group(1)), '')

    parse_deck_helper(deck_text, handle_card, is_names_line, extract_names_card_data)

class DeckFormat(str, Enum):
    TEXT = 'text'
    NAMES = 'names'

def parse_deck(deck_text: str, format: DeckFormat, handle_card: Callable) -> None:
    if format == DeckFormat.TEXT:
        return parse_text(deck_text, handle_card)
    elif format == DeckFormat.NAMES:
        return parse_names(deck_text, handle_card)
    else:
        raise ValueError('Unrecognized deck format.')
