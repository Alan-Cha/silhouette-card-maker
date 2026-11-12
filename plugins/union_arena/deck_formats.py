from re import compile, IGNORECASE
from enum import Enum
from typing import Callable, Tuple

card_data_tuple = Tuple[str, int, str]  # Card Number, Quantity, Name

# e.g. UE03BT/JJK-1-001, UE03BT/JJK-1-005_p1, UE03BT/JJK-1-005-ALT1, UEPR/2024-AP02, UAPR/IMS_AP04.
# The set prefix is optional so short numbers (JJK-1-001) are reported as errors instead of skipped.
CARD_NUMBER = r'(?:[A-Z0-9]+/)?[A-Z0-9]+(?:[-_][A-Z0-9]+)+'

def parse_deck_helper(deck_text: str, handle_card: Callable, is_card_line: Callable[[str], bool], extract_card_data: Callable[[str], card_data_tuple]) -> None:
    error_lines = []

    index = 0
    for line in deck_text.strip().split('\n'):
        line = line.strip()
        if is_card_line(line):
            index = index + 1

            card_number, quantity, name = extract_card_data(line)

            parts = [f'Index: {index}', f'quantity: {quantity}', f'card number: {card_number}']
            if name: parts.append(f'name: {name}')
            print(', '.join(parts))
            try:
                handle_card(index, card_number, quantity)
            except Exception as e:
                print(f'Error: {e}')
                error_lines.append((line, e))

        else:
            print(f'Skipping: "{line}"')

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

def parse_with_pattern(deck_text: str, handle_card: Callable, pattern) -> None:
    def extract_card_data(line) -> card_data_tuple:
        match = pattern.match(line)
        name = match.group('name') if 'name' in pattern.groupindex else ''
        return (match.group('card'), int(match.group('qty')), (name or '').strip())

    parse_deck_helper(deck_text, handle_card, lambda line: bool(pattern.match(line)), extract_card_data)

def parse_exburst(deck_text: str, handle_card: Callable) -> None:
    # '{Quantity} x {Card Number}', as exported by the ExBurst deck builder
    parse_with_pattern(deck_text, handle_card, compile(rf'^(?P<qty>\d+)\s*x\s+(?P<card>{CARD_NUMBER})\s*$', IGNORECASE))

def parse_text(deck_text: str, handle_card: Callable) -> None:
    # '{Quantity} {Card Number} {Name (optional)}'
    parse_with_pattern(deck_text, handle_card, compile(rf'^(?P<qty>\d+)\s+(?P<card>{CARD_NUMBER})(?:\s+(?P<name>.+))?$', IGNORECASE))

class DeckFormat(str, Enum):
    EXBURST = 'exburst'
    TEXT = 'text'

def parse_deck(deck_text: str, format: DeckFormat, handle_card: Callable) -> None:
    if format == DeckFormat.EXBURST:
        return parse_exburst(deck_text, handle_card)
    elif format == DeckFormat.TEXT:
        return parse_text(deck_text, handle_card)
    else:
        raise ValueError('Unrecognized deck format.')
