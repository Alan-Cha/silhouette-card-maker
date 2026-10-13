import os
from html import unescape
from re import DOTALL, compile, sub
from time import sleep
from typing import NamedTuple, Optional

import requests

from utilities import guess_extension

SEARCH_URL = 'https://www.fowtcg.com/card_search'
CARD_URL_TEMPLATE = 'https://www.fowtcg.com/card/{card_id}'

SEARCH_RESULT_PATTERN = compile(
    r'<a href="https://www\.fowtcg\.com/card/(\d+)">\s*'
    r'<img class="mb-4" src="([^"]+)">\s*'
    r'<h4 class="font-bold">([^<]*)</h4>\s*'
    r'<p class="mt-2 text-blue-700">([^<]*)</p>'
)
SET_CODE_PATTERN = compile(r'^[A-Z0-9]+-\d+J?$') # 'AVL-012', not promos like 'AVL Pre-Release Party'
DETAIL_IMAGE_PATTERN = compile(r'<img class="mb-12[^"]*" src="([^"]+)">')
DETAIL_NAME_PATTERN = compile(r'<div class="title-frame text-xl[^"]*">([^<]*)</div>')
DETAIL_CODE_PATTERN = compile(r'Card No\.</div>\s*<div[^>]*>([^<]*)</div>', DOTALL)

session = requests.Session()

class Card(NamedTuple):
    card_id: int
    image_url: str
    name: str
    code: str

def request_fowtcg(url: str, params: Optional[dict] = None) -> requests.Response:
    r = session.get(url, params=params, headers={'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'}, timeout=30)

    # Check for 2XX response code
    r.raise_for_status()

    sleep(0.15)

    return r

def normalize_name(name: str) -> str:
    return unescape(name).replace('’', "'").strip().casefold()

def search_card(name: str) -> Card:
    # The card search matches substrings of card names, so walk the result pages
    # until an exact name match turns up.
    page = 1
    matches = []
    while True:
        html = request_fowtcg(SEARCH_URL, {'free_text': name, 'page': page}).text
        matches += [
            Card(int(card_id), image_url, unescape(card_name), unescape(code))
            for card_id, image_url, card_name, code in SEARCH_RESULT_PATTERN.findall(html)
            if normalize_name(card_name) == normalize_name(name)
        ]

        if matches or f'page={page + 1}"' not in html:
            break
        page += 1

    if not matches:
        raise ValueError(f'Card "{name}" not found on fowtcg.com')

    # Results are newest first. Prefer the newest regular set printing over promos.
    return next((card for card in matches if SET_CODE_PATTERN.match(card.code)), matches[0])

def fetch_card_detail(card_id: int) -> Optional[Card]:
    try:
        html = request_fowtcg(CARD_URL_TEMPLATE.format(card_id=card_id)).text
    except requests.HTTPError:
        # The site answers unknown card ids with a 500, not a 404.
        return None

    image = DETAIL_IMAGE_PATTERN.search(html)
    name = DETAIL_NAME_PATTERN.search(html)
    code = DETAIL_CODE_PATTERN.search(html)
    if not (image and name and code):
        return None

    return Card(card_id, image.group(1), unescape(name.group(1)).strip(), unescape(code.group(1)).strip())

def find_back(card: Card) -> Optional[Card]:
    # The site lists the back of a double-sided ruler (J-ruler or order) as the next
    # card id with the same card number, so check that neighbouring card.
    back = fetch_card_detail(card.card_id + 1)
    if back and back.code.rstrip('J') == card.code.rstrip('J') and normalize_name(back.name) != normalize_name(card.name):
        return back
    return None

def fetch_image(url: str) -> bytes:
    r = request_fowtcg(url)

    content_type = r.headers.get('content-type', '')
    if not content_type.startswith('image/'):
        raise ValueError(f'Expected an image from {url}, got "{content_type}"')

    return r.content

def save_copies(image: bytes, directory: str, index: int, clean_name: str, quantity: int) -> None:
    extension = guess_extension(image)
    for counter in range(quantity):
        with open(os.path.join(directory, f'{index}{clean_name}{counter + 1}{extension}'), 'wb') as f:
            f.write(image)

def fetch_card_art(index: int, name: str, quantity: int, front_img_dir: str, double_sided_dir: str) -> None:
    card = search_card(name)
    clean_name = sub(r'[^\w]', '', card.name)

    save_copies(fetch_image(card.image_url), front_img_dir, index, clean_name, quantity)

    back = find_back(card)
    if back:
        print(f'Back: {back.name}')
        save_copies(fetch_image(back.image_url), double_sided_dir, index, clean_name, quantity)

def get_handle_card(front_img_dir: str, double_sided_dir: str):
    def configured_fetch_card(index: int, name: str, quantity: int):
        fetch_card_art(index, name, quantity, front_img_dir, double_sided_dir)

    return configured_fetch_card
