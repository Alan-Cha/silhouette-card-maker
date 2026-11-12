import os
from functools import cache
from re import sub
from time import sleep

import requests

from utilities import guess_extension

API_BASE = 'https://dtdb.co/api'
SITE_BASE = 'https://dtdb.co'

session = requests.Session()

def request_dtdb(query: str) -> requests.Response:
    r = session.get(query, headers={'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'}, timeout=30)

    # Check for 2XX response code
    r.raise_for_status()

    sleep(0.1)

    return r

# dtdb has no trailing-slash redirects, so these paths must be exact.
def fetch_dtdb_decklist(deck_id: str) -> dict:
    return request_dtdb(f'{API_BASE}/decklist/{deck_id}').json()

# One request for the whole card list (~1 MB) instead of one per card.
@cache
def fetch_cards() -> dict:
    return {card['code']: card for card in request_dtdb(f'{API_BASE}/cards').json()}

def remove_nonalphanumeric(s: str) -> str:
    return sub(r'[^\w]', '', s)

def fetch_card_art(index: int, code: str, quantity: int, front_img_dir: str) -> None:
    card = fetch_cards().get(code)
    if card is None:
        raise ValueError(f'Card "{code}" not found on dtdb')

    image_path = card.get('imagesrc')
    if not image_path:
        raise ValueError(f'No image available for card "{code}"')

    r = request_dtdb(f'{SITE_BASE}{image_path}')
    if not r.headers.get('content-type', '').startswith('image/'):
        raise ValueError(f'dtdb did not return an image for card "{code}"')

    card_art = r.content
    name = remove_nonalphanumeric(card.get('title') or '') or code
    extension = guess_extension(card_art, '.jpg')

    # Save image based on quantity
    for counter in range(quantity):
        with open(os.path.join(front_img_dir, f'{index}{name}{counter + 1}{extension}'), 'wb') as f:
            f.write(card_art)

def get_handle_card(front_img_dir: str):
    def configured_fetch_card(index: int, code: str, quantity: int):
        fetch_card_art(index, code, quantity, front_img_dir)

    return configured_fetch_card
