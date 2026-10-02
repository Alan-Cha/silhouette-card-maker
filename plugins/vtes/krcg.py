import os
from re import sub
from time import sleep
from urllib.parse import quote

import requests

from utilities import guess_extension

API_BASE = 'https://api.krcg.org'

session = requests.Session()

def request_krcg(url: str) -> requests.Response:
    r = session.get(url, headers={'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'}, timeout=30)

    # Check for 2XX response code
    r.raise_for_status()

    sleep(0.1)

    return r

def fetch_twda_deck(deck_id: str) -> dict:
    return request_krcg(f'{API_BASE}/twda/{quote(deck_id, safe="")}').json()

def fetch_card_json(id_or_name) -> dict:
    # KRCG resolves numeric card ids as well as card names, including
    # TWDA-style variants such as "Rack, The" or "Theo Bell (G2 ADV)".
    return request_krcg(f'{API_BASE}/card/{quote(str(id_or_name), safe="")}').json()

def fetch_card_art(index: int, id_or_name, quantity: int, front_img_dir: str) -> None:
    card = fetch_card_json(id_or_name)

    image_url = card.get('url')
    if not image_url:
        raise ValueError(f'No image available for card "{id_or_name}"')

    response = request_krcg(image_url)
    if not response.headers.get('content-type', '').startswith('image/'):
        raise ValueError(f'"{image_url}" did not return an image')

    clean_name = sub(r'[^\w]', '', card.get('name') or str(id_or_name))
    extension = guess_extension(response.content)

    for counter in range(quantity):
        image_path = os.path.join(front_img_dir, f'{index}{clean_name}{counter + 1}{extension}')

        with open(image_path, 'wb') as f:
            f.write(response.content)

def get_handle_card(front_img_dir: str):
    def configured_fetch_card(index: int, id_or_name, quantity: int):
        fetch_card_art(index, id_or_name, quantity, front_img_dir)

    return configured_fetch_card
