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

            print(f'Index: {index}, quantity: {quantity}, card ID: {card_id}, name: {name}')
            try:
                handle_card(index, card_id, quantity)
            except Exception as e:
                print(f'Error: {e}')
                error_lines.append((line, e))

        else:
            print(f'Skipping: "{line}"')

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

def parse_deckplanet(deck_text: str, handle_card: Callable) -> None:
    # '{Quantity} {Name} [{Card ID}]'; the Contender line has no quantity
    pattern = compile(r'^(?:(\d+)\s+)?(.+?)\s+\[([^\]]+)\]$')

    def is_deckplanet_line(line) -> bool:
        return bool(pattern.match(line))

    def extract_deckplanet_card_data(line) -> card_data_tuple:
        match = pattern.match(line)
        card_id = match.group(3).strip()
        quantity = int(match.group(1) or 1)
        name = match.group(2).strip()
        return (card_id, quantity, name)

    parse_deck_helper(deck_text, handle_card, is_deckplanet_line, extract_deckplanet_card_data)

class DeckFormat(str, Enum):
    DECKPLANET = 'deckplanet'

def parse_deck(deck_text: str, format: DeckFormat, handle_card: Callable) -> None:
    if format == DeckFormat.DECKPLANET:
        return parse_deckplanet(deck_text, handle_card)
    else:
        raise ValueError('Unrecognized deck format.')
