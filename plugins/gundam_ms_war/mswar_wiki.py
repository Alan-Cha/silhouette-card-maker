from functools import lru_cache
from os import path
from re import compile, IGNORECASE, MULTILINE
from time import sleep
from typing import Dict, List

from requests import Response, Session

from utilities import guess_extension

session = Session()

WIKI_API_URL = 'https://gundammswar.fandom.com/api.php'

OUTPUT_CARD_ART_FILE_TEMPLATE = '{deck_index}{card_number}_{quantity_counter}{extension}'

# Wiki file names look like 'MS_001_Wing_Gundam.jpg', 'BF_p02_St_louis,_MO.jpg',
# 'PL-P09_Kou_Uraki_promo.jpeg', 'Gp_bf-p19-heavyarmscustom.jpg', 'Gundam_card_BF-p01_...'.
FILE_NAME_PATTERN = compile(r'^(?:gundam_card_|gp_)?(ms|pl|ev|bf)[_-](p?\d+)', IGNORECASE)

# 'MS-011 Leo Common' lines on the wiki's 'Text Check List' page (numbered cards only, no promos or missions)
CHECKLIST_LINE_PATTERN = compile(r'^((?:MS|PL|EV|BF)-\d{3})\s+(.+?)\s+(?:Common|Uncommon|Rare|Holo|Gold)\s*$', MULTILINE)

def normalize_card_number(card_number: str) -> str:
    """'ms-1', 'MS_001', 'bf-p2' -> 'MS-001', 'MS-001', 'BF-P02'."""
    match = compile(r'^(ms|pl|ev|bf)[-_ ]?(p?)(\d+)$', IGNORECASE).match(card_number.strip())
    if not match:
        raise ValueError(f'Invalid card number "{card_number}"; expected e.g. MS-001, PL-015, EV-023, BF-p03')

    prefix, promo, number = match.groups()
    width = 2 if promo else 3
    return f'{prefix}-{promo}{number.zfill(width)}'.upper()

def request_wiki(url: str, params: dict = None) -> Response:
    r = session.get(url, params=params, headers={'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'})

    # Check for 2XX response code
    r.raise_for_status()

    sleep(0.1)

    return r

@lru_cache(maxsize=1)
def get_card_image_index() -> Dict[str, str]:
    """Map normalized card numbers to image URLs. The wiki has ~400 files, so one request covers it."""
    # Single page (ailimit=500); follow 'continue' if the wiki ever grows past 500 files
    json = request_wiki(WIKI_API_URL, {
        'action': 'query',
        'list': 'allimages',
        'ailimit': 500,
        'aiprop': 'url',
        'format': 'json',
    }).json()

    index = {}
    for image in json['query']['allimages']:
        match = FILE_NAME_PATTERN.match(image['name'])
        if match:
            index[normalize_card_number(match.group(1) + '-' + match.group(2))] = image['url']

    return index

def normalize_card_name(name: str) -> str:
    # The check list writes both 'Wing Gundam (Bird mode)' and 'Aries(flying mode)'
    return ' '.join(name.casefold().replace('(', ' (').split())

def parse_checklist(wikitext: str) -> Dict[str, List[str]]:
    """Map normalized card names to every card number printed with that name."""
    index = {}
    for card_number, name in CHECKLIST_LINE_PATTERN.findall(wikitext):
        index.setdefault(normalize_card_name(name), []).append(card_number)

    return index

@lru_cache(maxsize=1)
def get_card_name_index() -> Dict[str, List[str]]:
    json = request_wiki(WIKI_API_URL, {
        'action': 'parse',
        'page': 'Text Check List',
        'prop': 'wikitext',
        'format': 'json',
    }).json()

    return parse_checklist(json['parse']['wikitext']['*'])

def get_card_number_by_name(name: str) -> str:
    candidates = get_card_name_index().get(normalize_card_name(name), [])
    if not candidates:
        raise ValueError(f'No card named "{name}" on the Gundam M.S. War wiki check list; use the text format with a card number')
    if len(candidates) > 1:
        raise ValueError(f'Card name "{name}" matches several cards ({", ".join(candidates)}); use the text format with one of these card numbers')

    return candidates[0]

def fetch_card(index: int, card_number: str, quantity: int, front_img_dir: str):
    card_number = normalize_card_number(card_number)

    image_url = get_card_image_index().get(card_number)
    if image_url is None:
        raise ValueError(f'No image found on the Gundam M.S. War wiki for card "{card_number}"')

    # Without format=original, Fandom re-encodes the scan as WebP
    response = request_wiki(image_url, {'format': 'original'})
    content_type = response.headers.get('content-type', '')
    if not content_type.startswith('image/'):
        raise ValueError(f'Expected an image for card "{card_number}", got "{content_type}"')

    card_art = response.content
    extension = guess_extension(card_art)

    # Save image based on quantity
    for counter in range(quantity):
        image_path = path.join(front_img_dir, OUTPUT_CARD_ART_FILE_TEMPLATE.format(deck_index=str(index), card_number=card_number, quantity_counter=str(counter + 1), extension=extension))

        with open(image_path, 'wb') as f:
            f.write(card_art)

def get_handle_card(front_img_dir: str):
    def configured_fetch_card(index: int, card_number: str, quantity: int):
        fetch_card(index, card_number, quantity, front_img_dir)

    return configured_fetch_card

def get_handle_card_by_name(front_img_dir: str):
    def configured_fetch_card(index: int, name: str, quantity: int):
        fetch_card(index, get_card_number_by_name(name), quantity, front_img_dir)

    return configured_fetch_card
