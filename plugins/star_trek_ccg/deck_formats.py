from re import compile
from enum import Enum
from typing import Callable, Tuple

card_data_tuple = Tuple[str, int, str]  # Card Key, Quantity, Name

def parse_deck_helper(deck_text: str, handle_card: Callable, is_card_line: Callable[[str], bool], extract_card_data: Callable[[str], card_data_tuple]) -> None:
    error_lines = []

    index = 0
    for line in deck_text.strip().split('\n'):
        line = line.rstrip('\r')
        if is_card_line(line):
            index = index + 1

            card_key, quantity, name = extract_card_data(line)

            print(f'Index: {index}, quantity: {quantity}, name: {name}')
            try:
                handle_card(index, card_key, quantity)
            except Exception as e:
                print(f'Error: {e}')
                error_lines.append((line, e))

        else:
            print(f'Skipping: "{line}"')

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

# trekcc.org decklist text export, one card per line:
# '{Set}\t{Rarity}\t{Number}\t\t{Quantity}x {Name}', where missions omit '{Quantity}x '
def parse_trekcc(deck_text: str, handle_card: Callable) -> None:
    pattern = compile(r'^(\d+)\t([A-Z]+)\t(\d+)\t\t(?:(\d+)x )?(.+)$')

    def is_trekcc_line(line) -> bool:
        return bool(pattern.match(line))

    def extract_trekcc_card_data(line) -> card_data_tuple:
        match = pattern.match(line)
        # Collector info as printed on the card, e.g. '55V027'
        card_key = f'{match.group(1)}{match.group(2)}{int(match.group(3)):03}'
        quantity = int(match.group(4) or 1)
        name = match.group(5).strip()
        return (card_key, quantity, name)

    parse_deck_helper(deck_text, handle_card, is_trekcc_line, extract_trekcc_card_data)

# LackeyCCG deck text export: '{Quantity}\t{Name}'
def parse_lackey(deck_text: str, handle_card: Callable) -> None:
    pattern = compile(r'^(\d+)\t(.+)$')

    def is_lackey_line(line) -> bool:
        return bool(pattern.match(line))

    def extract_lackey_card_data(line) -> card_data_tuple:
        match = pattern.match(line)
        name = match.group(2).strip()
        return (name, int(match.group(1)), name)

    parse_deck_helper(deck_text, handle_card, is_lackey_line, extract_lackey_card_data)

class DeckFormat(str, Enum):
    LACKEY = 'lackey'
    TREKCC = 'trekcc'

def parse_deck(deck_text: str, format: DeckFormat, handle_card: Callable) -> None:
    if format == DeckFormat.LACKEY:
        return parse_lackey(deck_text, handle_card)
    elif format == DeckFormat.TREKCC:
        return parse_trekcc(deck_text, handle_card)
    else:
        raise ValueError('Unrecognized deck format.')
