import os
from enum import Enum
from re import compile, split
from typing import Callable, Iterable, Optional, Tuple

from plugins.vtes.krcg import fetch_twda_deck

card_data_tuple = Tuple[str, object, int] # name, card id or lookup name, quantity

def parse_deck_helper(
        lines: Iterable,
        handle_card: Callable,
        extract_card_data: Callable[[object], Optional[card_data_tuple]],
    ) -> None:
    error_lines = []

    index = 0

    for line in lines:
        card_data = extract_card_data(line)

        if card_data:
            index = index + 1

            name, card_id, quantity = card_data

            print(f'Index: {index}, quantity: {quantity}, card id: {card_id}, name: {name}')
            try:
                handle_card(index, card_id, quantity)
            except Exception as e:
                print(f'Error: {e}')
                error_lines.append((line, e))
        else:
            print(f'Skipping: "{line}"')

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

# Text format used by the TWDA, Amaranth, VDB and Lackey
#   Crypt (12 cards, min=8, max=21, avg=3.75)
#   2x Stick               3  ANI                      Nosferatu antitribu:4
#   1x Theo Bell (ADV)     7  CEL DOM POT              Brujah:2
#   Library (90 cards)
#   Master (12)
#   5x Blood Doll
#   1x Rack, The
# Lackey uses '{quantity}<tab>{name}' instead of '{quantity}x {name}'.
TEXT_LINE_PATTERN = compile(r'^(\d+)(?:x\s+|\t)(.+)$')
CRYPT_GROUP_PATTERN = compile(r':\s*(\d+|ANY)\s*$')
ADV_PATTERN = compile(r'\s*\(ADV\)$')

def extract_text_card_data(line: str) -> Optional[card_data_tuple]:
    match = TEXT_LINE_PATTERN.match(line)
    if not match:
        return None

    quantity = int(match.group(1))
    rest = match.group(2)

    # Crypt columns (capacity, disciplines, clan:group) and TWDA comments are
    # separated from the name by two or more spaces, a tab, or ' -- '.
    name = split(r'\s{2,}|\t| -- ', rest.strip())[0].strip()

    # Vampires with several groups share a name, so the group column picks the
    # card the same way KRCG names them: 'Stick (G4)', 'Theo Bell (G2 ADV)'.
    lookup_name = name
    group = CRYPT_GROUP_PATTERN.search(rest)
    if group and group.group(1).isdigit():
        is_adv = ADV_PATTERN.search(name)
        base_name = ADV_PATTERN.sub('', name)
        lookup_name = f'{base_name} (G{group.group(1)}{" ADV" if is_adv else ""})'

    return (name, lookup_name, quantity)

def parse_text(deck_text: str, handle_card: Callable) -> None:
    parse_deck_helper(
        [line.strip() for line in deck_text.strip().splitlines() if line.strip()],
        handle_card,
        extract_text_card_data,
    )

# TWDA deck id or a URL ending with it
#   2016gncbg
#   https://api.krcg.org/twda/2016gncbg
#   https://vdb.im/decks/2016gncbg
def parse_twda(deck_text: str, handle_card: Callable) -> None:
    if os.path.isfile(deck_text):
        with open(deck_text, 'r', encoding='utf-8-sig') as deck_file:
            deck_text = deck_file.read()

    deck_id = split(r'[/#=]', deck_text.strip().rstrip('/'))[-1]
    if not deck_id:
        print(f'"{deck_text}" is not a valid TWDA deck id or URL.')
        return

    data = fetch_twda_deck(deck_id)

    cards = list(data.get('crypt', {}).get('cards', []))
    for card_type in data.get('library', {}).get('cards', []):
        cards.extend(card_type.get('cards', []))

    parse_deck_helper(
        cards,
        handle_card,
        lambda card: (card['name'], card['id'], card['count']),
    )

class DeckFormat(str, Enum):
    TEXT = 'text'
    TWDA = 'twda'

def parse_deck(deck_text: str, format: DeckFormat, handle_card: Callable) -> None:
    if format == DeckFormat.TEXT:
        parse_text(deck_text, handle_card)
    elif format == DeckFormat.TWDA:
        parse_twda(deck_text, handle_card)
    else:
        raise ValueError('Unrecognized deck format.')
