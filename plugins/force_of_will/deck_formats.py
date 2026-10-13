from enum import Enum
from re import compile
from typing import Callable, List, Tuple

card_data_tuple = Tuple[str, int] # name, quantity

def parse_deck_helper(
        deck_text: str,
        handle_card: Callable,
        deck_splitter: Callable[[str], List[str]],
        is_card_line: Callable[[str], bool],
        extract_card_data: Callable[[str], card_data_tuple],
    ) -> None:
    error_lines = []

    index = 0

    for line in deck_splitter(deck_text):
        if is_card_line(line):
            index = index + 1

            name, quantity = extract_card_data(line)

            print(f'Index: {index}, quantity: {quantity}, name: {name}')
            try:
                handle_card(index, name, quantity)
            except Exception as e:
                print(f'Error: {e}')
                error_lines.append((line, e))
        else:
            print(f'Skipping: "{line}"')

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

# Plain text decklist, as written on tournament decklists and deck guides
#   Ruler
#   1 Lehen, Legendary Explorer
#   Main Deck
#   4 Group of Explorers
#   4x Silmeria, Explorer of Ruins
#   Magic Stone Deck
#   3 Light Magic Stone
def parse_fow(deck_text: str, handle_card: Callable) -> None:
    pattern = compile(r'^(\d+)x?\s+(.+?)\s*$') # '{quantity} {name}' or '{quantity}x {name}'

    def is_fow_line(line: str) -> bool:
        return bool(pattern.match(line))

    def extract_fow_card_data(line: str) -> card_data_tuple:
        match = pattern.match(line)
        return (match.group(2), int(match.group(1)))

    def split_fow_deck(deck_text: str) -> List[str]:
        return [line.strip() for line in deck_text.strip().splitlines() if line.strip()]

    parse_deck_helper(deck_text, handle_card, split_fow_deck, is_fow_line, extract_fow_card_data)

class DeckFormat(str, Enum):
    FOW = 'fow'

def parse_deck(deck_text: str, format: DeckFormat, handle_card: Callable) -> None:
    if format == DeckFormat.FOW:
        parse_fow(deck_text, handle_card)
    else:
        raise ValueError('Unrecognized deck format.')
