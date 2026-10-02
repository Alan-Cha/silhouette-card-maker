from os import path
from re import sub
from requests import Response, Session
from time import sleep

from utilities import guess_extension

session = Session()

# The official site hosts every officially released card. bssdb.dev also hosts the BSS07A and BSS07B sets,
# which the official site does not, so it is only tried when the official site has no image.
CARD_ART_URL_TEMPLATES = [
    'https://www.battlespirits-saga.com/images/cards/card/{image_key}.png',
    'https://www.bssdb.dev/cards/bss/{image_key}.png',
]

def request_battle_spirits_saga(query: str) -> Response:
    r = session.get(query, headers = {'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'}, timeout = 30)

    sleep(0.1)

    return r

def get_image_key(card_code: str) -> str:
    # bssdb.dev writes parallel cards as 'BSS01-039-p1', while their images are named 'BSS01-039_p1'
    return sub(r'-p(\d+)$', r'_p\1', card_code)

def fetch_card_art(image_key: str) -> bytes:
    for template in CARD_ART_URL_TEMPLATES:
        r = request_battle_spirits_saga(template.format(image_key=image_key))
        if r.status_code == 404:
            continue

        # Check for 2XX response code
        r.raise_for_status()

        content_type = r.headers.get('content-type', '')
        if not content_type.startswith('image/'):
            raise ValueError(f'Expected an image for {image_key} but got "{content_type}".')

        return r.content

    raise ValueError(f'No card image found for {image_key}.')

def fetch_card(index: int, card_code: str, quantity: int, front_img_dir: str):
    image_key = get_image_key(card_code)
    card_art = fetch_card_art(image_key)
    extension = guess_extension(card_art)

    # Save image based on quantity
    for counter in range(quantity):
        image_path = path.join(front_img_dir, f'{index}{image_key}{counter + 1}{extension}')

        with open(image_path, 'wb') as f:
            f.write(card_art)

def get_handle_card(front_img_dir: str):
    def configured_fetch_card(index: int, card_code: str, quantity: int):
        fetch_card(index, card_code, quantity, front_img_dir)

    return configured_fetch_card
