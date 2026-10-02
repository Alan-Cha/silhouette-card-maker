from enum import Enum
from json import loads
from os import path
from re import compile
from typing import Callable, List, Tuple

from plugins.universus.universus import get_card_id, get_universus_deck

card_data_tuple = Tuple[int, int] # card id, quantity

DECK_URL_PATTERN = compile(r'https?://(?:www\.)?universus\.cards/deck/([0-9a-fA-F-]{36})')
# '3 Chomp | Attack on Titan: Battle for Humanity'
TEXT_CARD_PATTERN = compile(r'^(\d+)\s+(.+?)\s+\|\s+(.+)$')

def parse_deck_helper(cards: List[card_data_tuple], handle_card: Callable) -> None:
    error_lines = []

    for index, (card_id, quantity) in enumerate(cards, start = 1):
        print(f'Index: {index}, quantity: {quantity}, card id: {card_id}')
        try:
            handle_card(index, card_id, quantity)
        except Exception as e:
            print(f'Error: {e}')
            error_lines.append((card_id, e))

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

def extract_universus_cards(deck: dict, ignore_sideboard: bool = False) -> List[card_data_tuple]:
    """
    universus.cards stores cards as [card id, mainboard count, sideboard count].
    The starting character comes first; mainboard and sideboard copies are combined.
    """
    counts = {}
    for card_id, main, side in deck.get('cards', []):
        side = 0 if ignore_sideboard else int(side)
        counts[int(card_id)] = counts.get(int(card_id), 0) + int(main) + side

    cards = [(card_id, quantity) for card_id, quantity in counts.items() if quantity > 0]

    starting_character = deck.get('startingCharacter')
    if starting_character is not None:
        starting_character = int(starting_character)
        rest = [card for card in cards if card[0] != starting_character]
        cards = [(starting_character, counts.get(starting_character) or 1)] + rest

    return cards

def parse_universus_json(deck_text: str, handle_card: Callable, ignore_sideboard: bool = False) -> None:
    parse_deck_helper(extract_universus_cards(loads(deck_text), ignore_sideboard), handle_card)

def parse_universus_text(deck_text: str, handle_card: Callable, ignore_sideboard: bool = False) -> None:
    """
    universus.cards "Display As: Decklist" text. Cards are looked up by name and set.
    The maybeboard is always skipped, like the other formats.
    """
    counts = {}
    section = ''
    for line in deck_text.strip().split('\n'):
        line = line.strip()
        if line.startswith('# '):
            section = line[2:].lower()
            continue

        match = TEXT_CARD_PATTERN.match(line)
        if not match:
            if line and not line.startswith('#'):
                print(f'Skipping: "{line}"')
            continue

        if section == 'maybeboard' or (ignore_sideboard and section == 'sideboard'):
            continue

        quantity, name, set_name = match.groups()
        try:
            card_id = get_card_id(name, set_name)
        except Exception as e:
            print(f'Error: {e}')
            continue

        # The starting character section comes first, so dict order keeps it first
        counts[card_id] = counts.get(card_id, 0) + int(quantity)

    parse_deck_helper(list(counts.items()), handle_card)

def parse_universus_url(deck_text: str, handle_card: Callable, ignore_sideboard: bool = False) -> None:
    cards = []
    for line in deck_text.strip().split('\n'):
        match = DECK_URL_PATTERN.search(line)
        if not match:
            if line.strip():
                print(f'Skipping: "{line.strip()}"')
            continue

        cards += extract_universus_cards(get_universus_deck(match.group(1)), ignore_sideboard)

    parse_deck_helper(cards, handle_card)

class DeckFormat(str, Enum):
    UNIVERSUS_URL = 'universus_url'
    UNIVERSUS_JSON = 'universus_json'
    UNIVERSUS_TEXT = 'universus_text'

def parse_deck(deck_text: str, format: DeckFormat, handle_card: Callable, ignore_sideboard: bool = False) -> None:
    # Allow a deck URL to be passed directly instead of a file path
    if path.isfile(deck_text):
        with open(deck_text, 'r', encoding = 'utf-8') as deck_file:
            deck_text = deck_file.read()

    if format == DeckFormat.UNIVERSUS_URL:
        parse_universus_url(deck_text, handle_card, ignore_sideboard)
    elif format == DeckFormat.UNIVERSUS_JSON:
        parse_universus_json(deck_text, handle_card, ignore_sideboard)
    elif format == DeckFormat.UNIVERSUS_TEXT:
        parse_universus_text(deck_text, handle_card, ignore_sideboard)
    else:
        raise ValueError('Unrecognized deck format.')
