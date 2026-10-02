import os
from html import unescape
from re import compile, sub
from time import sleep
from urllib.parse import quote

import requests

from utilities import guess_extension

DECK_URL_TEMPLATE = 'https://www.conquestdb.com/decks/{user}/{deck_id}/'
IMAGE_URL_TEMPLATE = 'https://www.conquestdb.com/static/images/CardImages/{image_name}.jpg'

# Deck pages embed the same text as their "Download Deck" button, with lines joined by '|||'
DECK_TEXT_PATTERN = compile(r'var deck_text = "(.*?)";')

session = requests.Session()

def request_conquestdb(url: str) -> requests.Response:
    r = session.get(url, headers={'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'}, timeout=30)

    # Check for 2XX response code
    r.raise_for_status()

    sleep(0.1)

    return r

def fetch_deck_text(user: str, deck_id: str) -> str:
    html = request_conquestdb(DECK_URL_TEMPLATE.format(user=user, deck_id=deck_id)).text

    match = DECK_TEXT_PATTERN.search(html)
    if not match:
        raise ValueError(f'Could not find a decklist on the ConquestDB page for deck "{deck_id}"')

    return unescape(match.group(1)).replace('|||', '\n')

# Mirrors ConquestDB's own name-to-image conversion, e.g.
#   "Maksim's Squadron"   -> Maksim's_Squadron
#   "Subject: Ω-X62113"   -> Subject_Ω-X62113
def card_image_name(name: str) -> str:
    return name.replace('"', '').replace(':', '').replace(' ', '_')

def fetch_card_image(image_name: str) -> bytes:
    r = request_conquestdb(IMAGE_URL_TEMPLATE.format(image_name=quote(image_name, safe="'!,")))

    content_type = r.headers.get('content-type', '')
    if not content_type.startswith('image/'):
        raise ValueError(f'Expected an image for "{image_name}" but got "{content_type}"')

    return r.content

def save_copies(image: bytes, directory: str, index: int, clean_name: str, quantity: int) -> None:
    extension = guess_extension(image, '.jpg')

    for counter in range(quantity):
        image_path = os.path.join(directory, f'{index}{clean_name}{counter + 1}{extension}')

        with open(image_path, 'wb') as f:
            f.write(image)

def fetch_card_art(
    index: int,
    name: str,
    quantity: int,
    warlord: bool,
    front_img_dir: str,
    double_sided_dir: str,
) -> None:
    image_name = card_image_name(name)
    clean_name = sub(r'[^\w]', '', name)

    save_copies(fetch_card_image(image_name), front_img_dir, index, clean_name, quantity)

    # Warlords are double-sided: the back is their bloodied side
    if warlord:
        save_copies(fetch_card_image(f'{image_name}_bloodied'), double_sided_dir, index, clean_name, quantity)

def get_handle_card(front_img_dir: str, double_sided_dir: str):
    def configured_fetch_card(index: int, name: str, quantity: int, warlord: bool):
        fetch_card_art(
            index,
            name,
            quantity,
            warlord,
            front_img_dir,
            double_sided_dir,
        )

    return configured_fetch_card
