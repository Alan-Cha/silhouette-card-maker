from re import compile
from enum import Enum
from html import unescape
from typing import Callable, List, Tuple

from plugins.lord_of_the_rings_tcg.lotrtcgpc import fetch_deck_html, get_card_art_url

card_data_tuple = Tuple[str, str, int] # name, image URL, quantity

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

            name, image_url, quantity = extract_card_data(line)

            parts = [f'Index: {index}', f'quantity: {quantity}']
            if name: parts.append(f'name: {name}')
            parts.append(f'image: {image_url}')
            print(', '.join(parts))
            try:
                handle_card(index, image_url, quantity)
            except Exception as e:
                print(f'Error: {e}')
                error_lines.append((line, e))
        else:
            print(f'Skipping: "{line}"')

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

def parse_gemp_id(deck_text: str, handle_card: Callable):
    # '{blueprint id}', '{quantity} {blueprint id}' or '{quantity}x {blueprint id}'
    pattern = compile(r'^(?:(\d+)\s*x?\s+)?(\d+_\d+[*T]*)\s*$')

    def is_gemp_id_line(line) -> bool:
        return bool(pattern.match(line))

    def extract_gemp_id_card_data(line) -> card_data_tuple:
        match = pattern.match(line)
        if match:
            quantity = int(match.group(1) or 1)
            blueprint_id = match.group(2)

            return (blueprint_id, get_card_art_url(blueprint_id), quantity)

    def split_gemp_id_deck(deck_text: str) -> List[str]:
        return deck_text.strip().split('\n')

    parse_deck_helper(deck_text, handle_card, split_gemp_id_deck, is_gemp_id_line, extract_gemp_id_card_data)

def parse_gemp_url(deck_text: str, handle_card: Callable):
    # '{quantity}x <span class="tooltip">{name}<span><img class="ttimage" src="{image URL}" ...'
    # The ring-bearer, the One Ring and sites have no quantity
    pattern = compile(r'(?:(\d+)x )?<span class="tooltip">(.*?)<span><img class="ttimage" src="([^"]+)"')

    def is_gemp_url_line(line) -> bool:
        return bool(pattern.search(line))

    def extract_gemp_url_card_data(line) -> card_data_tuple:
        match = pattern.search(line)
        if match:
            quantity = int(match.group(1) or 1)
            name = unescape(match.group(2))
            image_url = match.group(3)

            return (name, image_url, quantity)

    def split_gemp_url_deck(deck_text: str) -> List[str]:
        deck_url = deck_text.strip()
        if not deck_url.startswith(('http://', 'https://')):
            raise ValueError(f'Expected a Gemp deck URL, got "{deck_url}".')

        return fetch_deck_html(deck_url).split('<br/>')

    parse_deck_helper(deck_text, handle_card, split_gemp_url_deck, is_gemp_url_line, extract_gemp_url_card_data)

class DeckFormat(str, Enum):
    GEMP_ID = 'gemp_id'
    GEMP_URL = 'gemp_url'

def parse_deck(deck_text: str, format: DeckFormat, handle_card: Callable):
    if format == DeckFormat.GEMP_ID:
        parse_gemp_id(deck_text, handle_card)
    elif format == DeckFormat.GEMP_URL:
        parse_gemp_url(deck_text, handle_card)
    else:
        raise ValueError('Unrecognized deck format.')
