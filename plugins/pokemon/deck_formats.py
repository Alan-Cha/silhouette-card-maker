import json
from collections import Counter
from re import compile
from enum import Enum
from typing import Callable, Tuple

card_data_tuple = Tuple[str, int, str, str] # Name, Quantity, Set ID, Card Number

def parse_deck_helper(deck_text: str, handle_card: Callable, is_card_line: Callable[[str], bool], extract_card_data: Callable[[str], card_data_tuple]) -> None:
    error_lines = []

    index = 0
    for line in deck_text.strip().split('\n'):
        if is_card_line(line):
            index = index + 1

            name, quantity, set_id, card_no = extract_card_data(line)

            parts = [f'Index: {index}', f'quantity: {quantity}']
            if name: parts.append(f'name: {name}')
            if set_id: parts.append(f'set: {set_id}')
            if card_no: parts.append(f'card number: {card_no}')
            print(', '.join(parts))
            try:
                handle_card(index, name, set_id, card_no, quantity)
            except Exception as e:
                print(f'Error: {e}')
                error_lines.append((line, e))

        else:
            print(f'Skipping: "{line}"')

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

def parse_limitless(deck_text: str, handle_card: Callable) -> None:
    pattern = compile(r'^(\d+)\s(.+)\s(\S+)\s(\S+)$') # '{Quantity} {Name} {Set} {Number}'

    def is_limitless_line(line) -> bool:
        return bool(pattern.match(line))

    def extract_limitless_card_data(line) -> card_data_tuple:
        match = pattern.match(line)
        if match:
            card_name = match.group(2).strip()
            quantity = int(match.group(1).strip())
            set_id = match.group(3).strip()
            card_number = match.group(4).strip()

            return (card_name, quantity, set_id, card_number)

    parse_deck_helper(deck_text, handle_card, is_limitless_line, extract_limitless_card_data)

def parse_pkmtts(deck_text: str, handle_card: Callable) -> None:
    # pokemoncard.io export: a JSON array of strings, one entry per physical
    # card copy, formatted as '{set_id}-{card_no}' (plus a leading export
    # header string, which is ignored). There's no per-line structure here,
    # so this doesn't go through parse_deck_helper.
    code_pattern = compile(r'^([a-zA-Z0-9]+)-(\d+)$')

    try:
        data = json.loads(deck_text)
    except json.JSONDecodeError as e:
        raise ValueError(f'Could not parse pkmtts export as JSON: {e}')

    codes = [entry for entry in data if isinstance(entry, str) and code_pattern.match(entry)]
    counts = Counter(codes)

    error_lines = []
    index = 0
    for code, quantity in counts.items():
        index = index + 1

        match = code_pattern.match(code)
        set_id = match.group(1)
        card_no = match.group(2)
        name = ''  # pkmtts.io export doesn't include card names

        parts = [f'Index: {index}', f'quantity: {quantity}', f'set: {set_id}', f'card number: {card_no}']
        print(', '.join(parts))
        try:
            handle_card(index, name, set_id, card_no, quantity)
        except Exception as e:
            print(f'Error: {e}')
            error_lines.append((code, e))

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

class DeckFormat(str, Enum):
    LIMITLESS = 'limitless'
    PKMTTS = 'pkmtts'

def parse_deck(deck_text: str, format: DeckFormat, handle_card: Callable) -> None:
    if format == DeckFormat.LIMITLESS:
        return parse_limitless(deck_text, handle_card)
    elif format == DeckFormat.PKMTTS:
        return parse_pkmtts(deck_text, handle_card)
    else:
        raise ValueError('Unrecognized deck format.')
