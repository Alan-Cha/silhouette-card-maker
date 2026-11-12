from os import path
from requests import Response, Session
from time import sleep

from utilities import guess_extension

session = Session()

CARD_ART_URL_TEMPLATE = 'https://multi-deckplanet.us-southeast-1.linodeobjects.com/alpha_clash/{card_id}.webp'

# Double-faced cards and the image ID of their back face
BACK_FACES = {
    'AC2-T01': 'AC2-T01_b',
    'AC4-002': 'AC4-060',
    'AC4-060': 'AC4-002',
    'AC5-001': 'AC5-061',
    'AC5-061': 'AC5-001',
    'CG26-001': 'CG26-001_b',
    'CG26-001_mysterious_portal': 'CG26-001_mysterious_portal_b',
}

def request_deckplanet(query: str) -> Response:
    r = session.get(query, headers = {'user-agent': 'silhouette-card-maker/0.1', 'accept': 'image/*'}, timeout = 30)

    # Check for 2XX response code
    r.raise_for_status()

    sleep(0.15)

    return r

def fetch_card_art(card_id: str) -> bytes:
    r = request_deckplanet(CARD_ART_URL_TEMPLATE.format(card_id=card_id))

    content_type = r.headers.get('content-type', '')
    if not content_type.startswith('image/'):
        raise ValueError(f'Expected an image for {card_id}, got "{content_type}"')

    return r.content

def fetch_card(index: int, card_id: str, quantity: int, front_img_dir: str, double_sided_dir: str):
    card_art = fetch_card_art(card_id)
    back_art = fetch_card_art(BACK_FACES[card_id]) if card_id in BACK_FACES else None

    extension = guess_extension(card_art)

    # Save image based on quantity
    for counter in range(quantity):
        image_name = f'{index}{card_id}{counter + 1}{extension}'

        with open(path.join(front_img_dir, image_name), 'wb') as f:
            f.write(card_art)

        # The back must share the front's file name to be paired
        if back_art is not None:
            with open(path.join(double_sided_dir, image_name), 'wb') as f:
                f.write(back_art)

def get_handle_card(front_img_dir: str, double_sided_dir: str):
    def configured_fetch_card(index: int, card_id: str, quantity: int):
        fetch_card(index, card_id, quantity, front_img_dir, double_sided_dir)

    return configured_fetch_card
