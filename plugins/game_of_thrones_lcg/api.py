import os
from functools import lru_cache
from io import BytesIO
from re import sub
from time import sleep

import requests
from PIL import Image

from utilities import guess_extension

API_BASE = 'https://thronesdb.com/api/public'

session = requests.Session()

def request_thronesdb(query: str) -> requests.Response:
    r = session.get(query, headers={'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'}, timeout=30)

    # Check for 2XX response code
    r.raise_for_status()

    sleep(0.075)

    return r

def fetch_decklist(decklist_id: str) -> dict:
    return request_thronesdb(f'{API_BASE}/decklist/{decklist_id}.json').json()

# One request for every card instead of one per card in the deck.
@lru_cache(maxsize=1)
def fetch_card_catalog() -> dict:
    return {card['code']: card for card in request_thronesdb(f'{API_BASE}/cards/').json()}

def remove_nonalphanumeric(s: str) -> str:
    return sub(r'[^\w]', '', s)

def prepare_card_image(image_bytes: bytes) -> bytes:
    img = Image.open(BytesIO(image_bytes))

    # Plot cards are printed landscape but need to be laid out portrait
    # alongside the rest of the deck.
    if img.width <= img.height:
        return image_bytes

    buffer = BytesIO()
    img.rotate(-90, expand=True).save(buffer, format=img.format)
    return buffer.getvalue()

def fetch_card_art(index: int, code: str, quantity: int, front_img_dir: str) -> None:
    card = fetch_card_catalog().get(code)
    if not card:
        raise ValueError(f'Card "{code}" not found on ThronesDB')

    name = card.get('name') or code
    print(f'Index: {index}, quantity: {quantity}, code: {code}, name: {name}')

    image_url = card.get('image_url')
    if not image_url:
        raise ValueError(f'No image available for card "{code}"')

    r = request_thronesdb(image_url)
    if not r.headers.get('content-type', '').startswith('image/'):
        raise ValueError(f'Image URL for card "{code}" did not return an image: {image_url}')

    card_art = prepare_card_image(r.content)
    extension = guess_extension(card_art)
    clean_name = remove_nonalphanumeric(name)

    for counter in range(quantity):
        image_path = os.path.join(front_img_dir, f'{index}{clean_name}{counter + 1}{extension}')

        with open(image_path, 'wb') as f:
            f.write(card_art)

def get_handle_card(front_img_dir: str):
    def configured_fetch_card(index: int, code: str, quantity: int):
        fetch_card_art(index, code, quantity, front_img_dir)

    return configured_fetch_card
