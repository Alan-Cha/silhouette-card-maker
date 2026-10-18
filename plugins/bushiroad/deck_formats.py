from enum import Enum
from typing import Callable
from re import compile, search
import os

from plugins.bushiroad.bushiroad import fetch_decklist, resolve_image_url

def parse_bushiroad_url(deck_text: str, handle_card: Callable) -> None:
    DECKLOG_URL_PATTERN = compile(r'https?://(decklog(?:-en)?)\.bushiroad\.com/view/(\w+)\s*')

    if os.path.isfile(deck_text):
        deck_text = open(deck_text, 'r', encoding='utf-8').read()

    error_lines = []
    index = 0

    for line in deck_text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue

        match = DECKLOG_URL_PATTERN.match(line)
        if not match:
            print(f'Skipping: "{line}"')
            continue

        host, deck_code = match.group(1), match.group(2)
        game_title, deck = fetch_decklist(deck_code, host)
        print(f'Game: {game_title.value}')

        for card in deck:
            if card.get('name') is None or card.get('num') is None or card.get('img') is None:
                continue

            index = index + 1
            name = card.get('name').strip()
            quantity = int(card.get('num'))

            front_image = card.get('img', '').strip()
            front_url = resolve_image_url(game_title, front_image, host) if front_image else ''

            back_image = ''
            if card.get('custom_param') is not None and card.get('custom_param').get('is_bothsides'):
                back_image = card.get('custom_param').get('rev_img', '').strip()
            back_url = resolve_image_url(game_title, back_image, host) if back_image else ''

            parts = [f'Index: {index}', f'quantity: {quantity}']
            if name: parts.append(f'name: {name}')
            print(', '.join(parts))

            # Japanese names have no Latin characters and would sanitize to an empty filename
            file_name = name if search(r'[A-Za-z0-9]', name) else card.get('card_number', name)

            try:
                handle_card(index, file_name, front_url, back_url, quantity)
            except Exception as e:
                print(f'Error: {e}')
                error_lines.append((name, e))

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

class DeckFormat(str, Enum):
    BUSHIROAD_URL = 'bushiroad_url'

def parse_deck(deck_text: str, format: DeckFormat, handle_card: Callable) -> None:
    if format == DeckFormat.BUSHIROAD_URL:
        return parse_bushiroad_url(deck_text, handle_card)
    else:
        raise ValueError('Unrecognized deck format.')
