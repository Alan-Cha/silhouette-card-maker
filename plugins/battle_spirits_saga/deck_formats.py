from re import compile
from enum import Enum
from collections import Counter
from typing import Callable, List, Tuple

card_data_tuple = Tuple[str, str, int] # name, card code, quantity

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

            name, card_code, quantity = extract_card_data(line)

            parts = [f'Index: {index}', f'quantity: {quantity}']
            if card_code: parts.append(f'card code: {card_code}')
            if name: parts.append(f'name: {name}')
            print(', '.join(parts))
            try:
                handle_card(index, card_code, quantity)
            except Exception as e:
                print(f'Error: {e}')
                error_lines.append((line, e))
        else:
            print(f'Skipping: "{line}"')

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

def split_lines(deck_text: str) -> List[str]:
    return deck_text.strip().splitlines()

def parse_bssdb(deck_text: str, handle_card: Callable):
    pattern = compile(r'^(\d+)x\s+(\S+):\s*(.*?)\s*$') # '{quantity}x {card code}: {name}'

    def is_bssdb_line(line) -> bool:
        return bool(pattern.match(line))

    def extract_bssdb_card_data(line) -> card_data_tuple:
        match = pattern.match(line)
        if match:
            quantity = int(match.group(1))
            card_code = match.group(2)
            name = match.group(3)

            return (name, card_code, quantity)

    parse_deck_helper(deck_text, handle_card, split_lines, is_bssdb_line, extract_bssdb_card_data)

def parse_bssdb_tts(deck_text: str, handle_card: Callable):
    pattern = compile(r'^(\d+) (\S+)$') # '{quantity} {card code}', built by split_bssdb_tts_deck

    def is_bssdb_tts_line(line) -> bool:
        return bool(pattern.match(line))

    def extract_bssdb_tts_card_data(line) -> card_data_tuple:
        match = pattern.match(line)
        if match:
            return ('', match.group(2), int(match.group(1)))

    def split_bssdb_tts_deck(deck_text: str) -> List[str]:
        # Each '[code,code,...]' list repeats a code once per copy, so count copies to fetch each image once
        lines = []
        for line in split_lines(deck_text):
            line = line.strip()
            if line.startswith('[') and line.endswith(']'):
                codes = [code.strip() for code in line[1:-1].split(',') if code.strip()]
                lines.extend(f'{quantity} {code}' for code, quantity in Counter(codes).items())
            else:
                lines.append(line)
        return lines

    parse_deck_helper(deck_text, handle_card, split_bssdb_tts_deck, is_bssdb_tts_line, extract_bssdb_tts_card_data)

class DeckFormat(str, Enum):
    BSSDB = 'bssdb'
    BSSDB_TTS = 'bssdb_tts'

def parse_deck(deck_text: str, format: DeckFormat, handle_card: Callable):
    if format == DeckFormat.BSSDB:
        parse_bssdb(deck_text, handle_card)
    elif format == DeckFormat.BSSDB_TTS:
        parse_bssdb_tts(deck_text, handle_card)
    else:
        raise ValueError('Unrecognized deck format.')
