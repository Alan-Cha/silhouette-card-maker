import re

from enum import Enum
from typing import Tuple, Callable

# Name, Enchanted, Quantity
card_data_tuple = Tuple[str, bool, int]

def parse_deck_helper(deck_text: str, is_card_line: Callable[[str], bool], extract_card_data: Callable[[str], card_data_tuple], handle_card: Callable) -> None:
    error_lines = []

    index = 0
    for line in deck_text.strip().split('\n'):
        if is_card_line(line):
            index = index + 1

            name, enchanted, quantity = extract_card_data(line)

            print(f'Index: {index}, quantity: {quantity}, name: {name}, enchanted: {enchanted}')
            # try:
            handle_card(index, name, enchanted, quantity)
            # except Exception as e:
            #     print(f'Error: {e}')
            #     error_lines.append((line, e))

        else:
            print(f'Skipping: "{line}"')

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

def parse_dreamborn_list(deck_text, handle_card) -> None:
    pattern = re.compile(r'(\d+)x?\s+(.+)', re.IGNORECASE)

    def is_dreamborn_card_line(line) -> bool:
        return bool(pattern.match(line))

    def extract_dreamborn_card_data(line) -> card_data_tuple:
        match = pattern.match(line)
        quantity = int(match.group(1))
        enchanted = False
        name = match.group(2).strip()

        if "*E*" in name:
            enchanted = True
            name = name.replace("*E*","")

        return (name, enchanted, quantity)

    parse_deck_helper(deck_text, is_dreamborn_card_line, extract_dreamborn_card_data, handle_card)

class DeckFormat(str, Enum):
    DREAMBORN = "dreamborn"

def parse_deck(deck_text: str, format: DeckFormat, handle_card) -> None:
    if format == DeckFormat.DREAMBORN:
        parse_dreamborn_list(deck_text, handle_card)
    else:
        raise ValueError("Unrecognized deck format")