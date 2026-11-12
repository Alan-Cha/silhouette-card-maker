import os
from io import BytesIO
from re import sub
from time import sleep

import requests
from PIL import Image

from utilities import guess_extension

API_BASE = 'https://marvelcdb.com/api/public'
IMAGE_URL_TEMPLATE = 'https://marvelcdb.com{image_path}'
# Cerebro (the community Marvel Champions Discord bot) image store, used when
# MarvelCDB has no image. Codes are upper-case there, e.g. 29002A.
CEREBRO_IMAGE_URL_TEMPLATE = 'https://cerebrodatastorage.blob.core.windows.net/cerebro-cards/official/{code}.jpg'

session = requests.Session()

def request_marvelcdb(
    query: str,
    allow_redirects: bool = True,
    retry_count: int = 0,
) -> requests.Response:
    # MarvelCDB is slow and occasionally drops connections or returns 5XX,
    # so retry those a few times with a growing wait.
    try:
        r = session.get(query, headers={'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'},
                        allow_redirects=allow_redirects, timeout=30)
        if r.status_code >= 500:
            r.raise_for_status()
    except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as e:
        if retry_count >= 3:
            raise
        print(f'Request to {query} failed ({e}), waiting {2 ** retry_count} seconds before retry {retry_count + 1}/3...')
        sleep(2 ** retry_count)
        return request_marvelcdb(query, allow_redirects, retry_count + 1)

    # Check for 2XX response code
    r.raise_for_status()

    sleep(0.075)

    return r

def fetch_marvelcdb_deck(deck_id: str, is_decklist: bool) -> dict:
    key = 'decklist' if is_decklist else 'deck'
    r = request_marvelcdb(f'{API_BASE}/{key}/{deck_id}.json', allow_redirects=False)

    # Private decks redirect to the login page and missing decklists return an
    # empty body, rather than an HTTP error.
    if r.status_code != 200 or not r.content:
        raise ValueError(f'MarvelCDB {key} {deck_id} is private or does not exist.')

    return r.json()

def fetch_card_json(code: str) -> dict:
    return request_marvelcdb(f'{API_BASE}/card/{code}.json').json()

def remove_nonalphanumeric(s: str) -> str:
    return sub(r'[^\w]', '', s)

def fetch_card_image(image_url: str) -> tuple[Image.Image, str]:
    image_bytes = request_marvelcdb(image_url).content
    img = Image.open(BytesIO(image_bytes))

    # Main schemes and some side schemes are printed landscape but need to be
    # laid out portrait alongside the rest of the deck.
    if img.width > img.height:
        img = img.rotate(-90, expand=True)

    return img, guess_extension(image_bytes)

def fetch_card_face(card: dict) -> tuple[Image.Image, str] | None:
    image_path = card.get('imagesrc')

    # Reprints have no image of their own, only a pointer to the original.
    if not image_path and card.get('duplicate_of_code'):
        image_path = fetch_card_json(card['duplicate_of_code']).get('imagesrc')

    if image_path:
        return fetch_card_image(IMAGE_URL_TEMPLATE.format(image_path=image_path))

    if not card.get('code'):
        return None

    try:
        return fetch_card_image(CEREBRO_IMAGE_URL_TEMPLATE.format(code=card['code'].upper()))
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            return None
        raise

def fetch_card_art(
    index: int,
    code: str,
    quantity: int,
    front_img_dir: str,
    double_sided_dir: str,
) -> None:
    card = fetch_card_json(code)

    name = card.get('name') or code
    clean_name = remove_nonalphanumeric(name)

    print(f'Index: {index}, quantity: {quantity}, code: {code}, name: {name}')

    front = fetch_card_face(card)
    if not front:
        raise ValueError(f'MarvelCDB has no image for {code} {name} yet.')

    front_img, front_ext = front
    for counter in range(quantity):
        front_img.save(os.path.join(front_img_dir, f'{index}{clean_name}{counter + 1}{front_ext}'))

    # Double-sided cards either carry their own back image (main schemes,
    # some villains) or link out to a separate card entry that holds it
    # (hero/alter-ego identities via linked_to_code).
    back = None
    if card.get('backimagesrc'):
        back = fetch_card_image(IMAGE_URL_TEMPLATE.format(image_path=card['backimagesrc']))
    elif card.get('linked_card'):
        back = fetch_card_face(card['linked_card'])

    if back:
        back_img, back_ext = back
        for counter in range(quantity):
            back_img.save(os.path.join(double_sided_dir, f'{index}{clean_name}{counter + 1}{back_ext}'))
    elif card.get('double_sided') or card.get('linked_to_code'):
        print(f'Warning: "{name}" ({code}) is double-sided but has no back image available yet.')

def get_handle_card(front_img_dir: str, double_sided_dir: str):
    def configured_fetch_card(index: int, code: str, quantity: int):
        fetch_card_art(
            index,
            code,
            quantity,
            front_img_dir,
            double_sided_dir,
        )

    return configured_fetch_card
