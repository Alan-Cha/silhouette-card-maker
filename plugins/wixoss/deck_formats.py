from enum import Enum
from html import unescape
from re import compile
from typing import Callable, List, Tuple

from plugins.wixoss.wixoss import fetch_deck_page

card_data_tuple = Tuple[str, int, str]  # Card Number, Quantity, Name

DECK_URL_PATTERN = compile(r'^https?://(www\.)?wixosstcg\.eu/deck/\d+')

# One card row on a wixosstcg.eu deck page, covering both the LRIG DECK and MAIN sections:
# <div Class="colqta col-xs-1">1</div><div class="colcod col-xs-2">WXDi-CP02-004[EN]</div><div class="colname col-xs-6"><a href="#" class="viscarta" data-id="2157">Gehenna Prefect Team</a></div>
CARD_ROW_PATTERN = compile(r'colqta[^>]*>\s*(\d+)\s*</div>\s*<div[^>]*colcod[^>]*>\s*([^<]+?)\s*</div>\s*<div[^>]*colname[^>]*>\s*<a[^>]*>([^<]*)</a>')

def parse_deck_helper(deck_text: str, handle_card: Callable, is_deck_line: Callable[[str], bool], extract_cards: Callable[[str], List[card_data_tuple]]) -> None:
    error_lines = []

    index = 0
    for line in deck_text.strip().split('\n'):
        line = line.strip()
        if not is_deck_line(line):
            print(f'Skipping: "{line}"')
            continue

        for card_number, quantity, name in extract_cards(line):
            index = index + 1

            print(f'Index: {index}, quantity: {quantity}, card number: {card_number}, name: {name}')
            try:
                handle_card(index, card_number, quantity)
            except Exception as e:
                print(f'Error: {e}')
                error_lines.append((card_number, e))

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

def extract_wixosstcg_cards(page_html: str) -> List[card_data_tuple]:
    return [(card_number, int(quantity), unescape(name).strip()) for quantity, card_number, name in CARD_ROW_PATTERN.findall(page_html)]

# wixosstcg.eu deck URL format
#   https://www.wixosstcg.eu/deck/19408/Sorasaki_Hina
def parse_wixosstcg_url(deck_text: str, handle_card: Callable) -> None:
    def is_wixosstcg_line(line) -> bool:
        return bool(DECK_URL_PATTERN.match(line))

    def extract_wixosstcg_line_cards(line) -> List[card_data_tuple]:
        return extract_wixosstcg_cards(fetch_deck_page(line))

    parse_deck_helper(deck_text, handle_card, is_wixosstcg_line, extract_wixosstcg_line_cards)

class DeckFormat(str, Enum):
    WIXOSSTCG_URL = 'wixosstcg_url'

def parse_deck(deck_text: str, format: DeckFormat, handle_card: Callable) -> None:
    if format == DeckFormat.WIXOSSTCG_URL:
        return parse_wixosstcg_url(deck_text, handle_card)
    else:
        raise ValueError('Unrecognized deck format.')
