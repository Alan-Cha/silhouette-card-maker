from html import unescape
from os import path
from re import compile, sub
from time import sleep
from unicodedata import normalize

import requests

from utilities import guess_extension

BASE_URL = 'https://dm.takaratomy.co.jp'
SEARCH_URL = f'{BASE_URL}/card/'
DETAIL_URL = f'{BASE_URL}/card/detail/'

SEARCH_RESULT_PATTERN = compile(r"<img class='cardImage' data-href='/card/detail/\?id=([\w-]+)'")
CARD_IMAGE_PATTERN = compile(r'<img src="(/wp-content/card/cardimage/[^"]+)" alt="([^"]*)"')

OUTPUT_CARD_ART_FILE_TEMPLATE = '{deck_index}{card_id}{quantity_counter}{extension}'

session = requests.Session()
session.headers.update({'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'})

def request_takaratomy(method: str, url: str, **kwargs) -> requests.Response:
    r = session.request(method, url, timeout=30, **kwargs)

    # Check for 2XX response code
    r.raise_for_status()

    sleep(0.5)

    return r

def normalize_name(name: str) -> str:
    # Decklists and the card database mix full-width and half-width characters (e.g. '＆' and '&')
    return sub(r'\s', '', normalize('NFKC', name))

def fetch_card_faces(card_id: str) -> list[tuple[str, str]]:
    # Each face of a card is an image on its detail page: one for normal cards and twinpacts,
    # a front and a back for psychic, dragheart, and other double-sided cards
    html = request_takaratomy('GET', DETAIL_URL, params={'id': card_id}).text
    faces = [(f'{BASE_URL}{src}', unescape(alt)) for src, alt in CARD_IMAGE_PATTERN.findall(html)]
    if not faces:
        raise ValueError(f'No card found with id "{card_id}"')
    return faces

def search_card_ids(name: str) -> list[str]:
    # Twinpacts are listed as 'Creature / Spell', but the search only matches one side's name
    keyword = name.split(' / ')[0]
    html = request_takaratomy('POST', SEARCH_URL, data={'keyword': keyword, 'keyword_type[]': 'card_name', 'pagenum': '1'}).text
    return SEARCH_RESULT_PATTERN.findall(html)

def find_card(name: str) -> tuple[str, list[tuple[str, str]]]:
    # The search matches partial names, so check each result for an exact match
    target = normalize_name(name)
    for card_id in search_card_ids(name):
        faces = fetch_card_faces(card_id)
        if normalize_name(faces[0][1]) == target:
            return card_id, faces
    raise ValueError(f'No card found with name "{name}"')

def download_image(url: str) -> bytes:
    r = request_takaratomy('GET', url)
    content_type = r.headers.get('content-type', '')
    if not content_type.startswith('image/'):
        raise ValueError(f'Expected an image from {url}, got "{content_type}"')
    return r.content

def save_copies(image: bytes, directory: str, index: int, card_id: str, quantity: int) -> None:
    extension = guess_extension(image)
    for counter in range(quantity):
        image_path = path.join(directory, OUTPUT_CARD_ART_FILE_TEMPLATE.format(deck_index=str(index), card_id=card_id, quantity_counter=str(counter + 1), extension=extension))

        with open(image_path, 'wb') as f:
            f.write(image)

def fetch_card(
    index: int,
    quantity: int,
    card_id: str,
    name: str,
    front_img_dir: str,
    double_sided_dir: str,
):
    if card_id:
        faces = fetch_card_faces(card_id)
    else:
        card_id, faces = find_card(name)

    save_copies(download_image(faces[0][0]), front_img_dir, index, card_id, quantity)

    if len(faces) > 1:
        save_copies(download_image(faces[1][0]), double_sided_dir, index, card_id, quantity)

def get_handle_card(
    front_img_dir: str,
    double_sided_dir: str,
):
    def configured_fetch_card(index: int, card_id: str, name: str, quantity: int = 1):
        fetch_card(
            index,
            quantity,
            card_id,
            name,
            front_img_dir,
            double_sided_dir,
        )

    return configured_fetch_card
