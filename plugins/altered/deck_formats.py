from re import compile
from enum import Enum
from _collections_abc import Set
from typing import Callable, Dict, Optional, Tuple

card_data_tuple = Tuple[str, int] # QR, Quantity

def parse_deck_helper(deck_text: str, handle_card: Callable, is_card_line: Callable[[str], bool], extract_card_data: Callable[[str], card_data_tuple]) -> None:
    error_lines = []

    index = 0
    for line in deck_text.strip().split('\n'):
        if is_card_line(line):
            index = index + 1

            qr_code, quantity = extract_card_data(line)

            print(f'Index: {index}, quantity: {quantity}, qr code: {qr_code}')
            try:
                handle_card(index, qr_code, quantity)
            except Exception as e:
                print(f'Error: {e}')
                error_lines.append((line, e))

        else:
            print(f'Skipping: "{line}"')

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

def parse_ajordat(deck_text: str, handle_card: Callable) -> None:
    pattern = compile(r'^(\d{1})\s+(.+)$') # Quantity QR

    def is_ajordat_line(line) -> bool:
        return bool(pattern.match(line))
    
    def extract_ajordat_card_data(line) -> card_data_tuple:
        match = pattern.match(line)
        if match:
            qr_code = match.group(2).strip()
            quantity = int( match.group(1).strip() )

            return (qr_code, quantity)
        
    parse_deck_helper(deck_text, handle_card, is_ajordat_line, extract_ajordat_card_data)

class DeckFormat(str, Enum):
    AJORDAT = "ajordat"

def parse_deck(deck_text: str, format: DeckFormat, handle_card: Callable) -> None:
    if format == DeckFormat.AJORDAT:
        return parse_ajordat(deck_text, handle_card)
    else:
        raise ValueError("Unrecognized deck format.")

if __name__ == '__main__':
    parse_deck()