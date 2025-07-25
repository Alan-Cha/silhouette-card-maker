import json
import re

from enum import Enum
from typing import Callable, Tuple

card_data_tuple = Tuple[str, str, int, int]

def parse_deck_helper(deck_text: str, is_card_line: Callable[[str], bool], extract_card_data: Callable[[str], card_data_tuple], handle_card: Callable) -> None:
    error_lines = []

    index = 0
    for line in deck_text.strip().split('\n'):
        if is_card_line(line):
            index = index + 1

            name, set_code, collector_number, quantity = extract_card_data(line)

            print(f'Index: {index}, quantity: {quantity}, set code: {set_code}, collector number: {collector_number}, name: {name}')
            try:
                handle_card(index, name, set_code, collector_number, quantity)
            except Exception as e:
                print(f'Error: {e}')
                error_lines.append((line, e))

        else:
            print(f'Skipping: "{line}"')

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')


#4 Arven OBF 186
#4 Iono PAL 185
#3 Boss's Orders PAL 172
#2 Professor's Research JTG 155
# {quant} {name} {set_id} {collector_number}
def parse_limitless_list(deck_text, handle_card) -> None:
    pattern = re.compile(r'^(?P<count>\d+)\s+(?P<name>.+?)\s+(?P<set>[A-Z]+)\s+(?P<number>\d+)\b.*$')
    def is_limitless_card_line(line: str) -> bool:
        return bool(pattern.match(line))

    def extract_limitless_card_data(line: str) -> card_data_tuple:
        match = pattern.match(line)
        quantity = int(match.group(1))
        name = match.group(2).strip()
        set_code = match.group(3).strip()
        collector_number = int(match.group(4))

        return (name, set_code, collector_number, quantity)
    
    parse_deck_helper(deck_text, is_limitless_card_line, extract_limitless_card_data, handle_card)

class DeckFormat(str, Enum):
    LIMITLESS = "limitless"

def parse_deck(deck_text: str, format: DeckFormat, handle_card) -> None:
    if format == DeckFormat.LIMITLESS:
        parse_limitless_list(deck_text, handle_card)
    else:
        raise ValueError("Unrecognized deck format")