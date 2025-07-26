from re import compile
from enum import Enum
from _collections_abc import Set
from typing import Callable, Dict, Optional, Tuple
from base64 import b64decode
from riftmana import fetch_card_number

card_data_tuple = Tuple[str, str, int] # Name, Card Number, Quantity 

def parse_deck_helper(deck_text: str, handle_card: Optional[Callable],
                      deck_splitter: Callable[[str], Set[str]], is_card_line: Callable[[str], bool], extract_card_data: Callable[[str], card_data_tuple],
                      ) -> Dict[str, int]:
    error_lines = []
    deck: Dict[str, int] = {}

    index = 0

    for line in deck_splitter(deck_text):
        if is_card_line(line):
            index = index + 1

            name, card_number, quantity = extract_card_data(line)

            print(f'Index: {index}, quantity: {quantity}, card number: {card_number}, name: {name}')

            deck[card_number] = deck.get(card_number, 0) + quantity
        else:
            print(f'Skipping: "{line}"')

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

    return deck

def parse_tts(deck_text: str, handle_card: Optional[Callable]) -> Dict[str, int]:
    pattern = compile(r'^([A-Z0-9]+)-(\d+[a-z]?)-(\d+)$') # '{Set ID}-{Card ID}-{Art Number}'
    alternate_art_suffix = 'a'

    def is_tts_line(line) -> bool:
        return bool(pattern.match(line))
    
    def extract_tts_card_data(line) -> card_data_tuple:
        match = pattern.match(line)
        if match:
            card_number = f'{ match.group(1).strip() }-{ match.group(2).strip() }'

            if int(match.group(3)) > 1:
                card_number = f'{card_number}{alternate_art_suffix}' # Assume that the desired art is the alternate art

            return ('', card_number, 1)

    def split_tts_deck(deck_text: str) -> Set[str]:
        return deck_text.strip().split(' ')
        
    return parse_deck_helper(deck_text, handle_card, split_tts_deck, is_tts_line, extract_tts_card_data)

def parse_pixelborn(deck_text: str, handle_card: Optional[Callable]) -> Dict[str, int]:
    pattern = compile(r'^([A-Z0-9]+)-(\d+[a-z]?)-(\d+)$') # '{Set ID}-{Card ID}-{Art Number}'
    alternate_art_suffix = 'a'

    def is_pixelborn_line(line) -> bool:
        return bool(pattern.match(line))
    
    def extract_pixelborn_card_data(line) -> card_data_tuple:
        match = pattern.match(line)
        if match:
            card_number = f'{ match.group(1).strip() }-{ match.group(2).strip() }'

            if int(match.group(3)) > 1:
                card_number = f'{card_number}{alternate_art_suffix}' # Assume that the desired art is the alternate art

            return ('', card_number, 1)

    def split_pixelborn_deck(deck_text: str) -> Set[str]:
        decoded = b64decode(deck_text).decode()
        return decoded.split('$')
    
    return parse_deck_helper(deck_text, handle_card, split_pixelborn_deck, is_pixelborn_line, extract_pixelborn_card_data)

def parse_piltover_archive(deck_text: str, handle_card: Optional[Callable]) -> Dict[str, int]:
    pattern = compile(r'^(\d+) (.+)$') # '{Quantity} {Card Name}'

    def is_piltover_archive_line(line) -> bool:
        return bool(pattern.match(line))
    
    def extract_piltover_archive_card_data(line) -> card_data_tuple:
        match = pattern.match(line)
        if match:
            quantity = int(match.group(1))
            name = match.group(2)
            card_number = fetch_card_number(name)

            return (name, card_number, quantity)

    def split_piltover_archive_deck(deck_text: str) -> Set[str]:
        return deck_text.strip().split('\n')

    return parse_deck_helper(deck_text, handle_card, split_piltover_archive_deck, is_piltover_archive_line, extract_piltover_archive_card_data)


class DeckFormat(str, Enum):
    TTS       = 'tts'
    PIXELBORN = 'pixelborn'
    PILTOVER  = 'piltover_archive'

def parse_deck(deck_text: str, format: DeckFormat, handle_card: Optional[Callable] = None) -> Dict[str, int]:
    if format == DeckFormat.TTS:
        return parse_tts(deck_text, handle_card)
    elif format == DeckFormat.PIXELBORN:
        return parse_pixelborn(deck_text, handle_card)
    elif format == DeckFormat.PILTOVER:
        return parse_piltover_archive(deck_text, handle_card)
    else:
        raise ValueError('Unrecognized deck format.')

if __name__ == '__main__':
    parse_deck()