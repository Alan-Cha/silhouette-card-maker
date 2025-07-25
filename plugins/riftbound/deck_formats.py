from re import compile
from enum import Enum
from _collections_abc import Set
from typing import Callable, Dict, Optional, Tuple
from base64 import b64decode

card_data_tuple = Tuple[str, str, int] # Name, Card Number, Quantity 

def parse_deck_helper(deck_text: str, handle_card: Optional[Callable],
                      deck_splitter: Callable[[str], Set[str]], is_card_line: Callable[[str], bool], extract_card_data: Callable[[str], card_data_tuple],
                      card_searcher: Optional[Callable[[str], str]] = None,
                      ) -> Dict[str, int]:
    error_lines = []
    deck: Dict[str, int] = {}

    index = 0

    for line in deck_splitter(deck_text):
        if is_card_line(line):
            index = index + 1

            name, card_number, quantity = extract_card_data(line)

            print(f'Index: {index}, quantity: {quantity}, card number: {card_number}, name: {name}')

            if card_number is None and name is not None and card_searcher is not None:
                card_number = card_searcher(name) # Currently not utilized due to authorization issues, but would be the solution to extracting by card name...

            deck[card_number] = deck.get(card_number, 0) + 1
        else:
            print(f'Skipping: "{line}"')

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

    return deck

def parse_tts(deck_text: str, handle_card: Optional[Callable]) -> Dict[str, int]:
    pattern = compile(r'^(\D{3})-(\d{3}\D\\|\d{3})-(\d+)$') # SET-CARD-ART
    alternate_art_suffix = 'a'

    def is_tts_line(line) -> bool:
        return bool(pattern.match(line))
    
    def extract_tts_card_data(line) -> card_data_tuple:
        match = pattern.match(line)
        if match:
            card_number = f'{ match.group(1).strip() }-{ match.group(2).strip() }'

            if int(match.group(3)) > 1:
                card_number = f'{card_number}{alternate_art_suffix}' # Assume that the desired art is the alternate art

            return ("", card_number, 1)

    def split_tts_deck(deck_text: str) -> Set[str]:
        return deck_text.strip().split(' ')
        
    return parse_deck_helper(deck_text, handle_card, split_tts_deck, is_tts_line, extract_tts_card_data)

def parse_pixelborn(deck_text: str, handle_card: Optional[Callable]) -> Dict[str, int]:
    pattern = compile(r'^(\D{3})-(\d{3}\D\\|\d{3})-(\d+)$') # SET-CARD-ART
    alternate_art_suffix = 'a'

    def is_pixelborn_line(line) -> bool:
        return bool(pattern.match(line))
    
    def extract_pixelborn_card_data(line) -> card_data_tuple:
        match = pattern.match(line)
        if match:
            card_number = f'{ match.group(1).strip() }-{ match.group(2).strip() }'

            if int(match.group(3)) > 1:
                card_number = f'{card_number}{alternate_art_suffix}' # Assume that the desired art is the alternate art

            return ("", card_number, 1)

    def split_pixelborn_deck(deck_text: str) -> Set[str]:
        decoded = b64decode(deck_text).decode()
        return decoded.split('$')
    
    return parse_deck_helper(deck_text, handle_card, split_pixelborn_deck, is_pixelborn_line, extract_pixelborn_card_data)

class DeckFormat(str, Enum):
    TTS       = "tts"
    PIXELBORN = "pixelborn"

def parse_deck(deck_text: str, format: DeckFormat, handle_card: Optional[Callable] = None) -> Dict[str, int]:
    if format == DeckFormat.TTS:
        return parse_tts(deck_text, handle_card)
    elif format == DeckFormat.PIXELBORN:
        return parse_pixelborn(deck_text, handle_card)
    else:
        raise ValueError("Unrecognized deck format.")

if __name__ == '__main__':
    parse_deck()