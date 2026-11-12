from functools import cache
from os import path
from re import sub
from time import sleep
from typing import Optional

from requests import Response, Session

from utilities import guess_extension

API_BASE = 'https://www.emeralddb.org/api'

session = Session()

def request_emeralddb(query: str) -> Response:
    r = session.get(query, headers={'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'}, timeout=30)

    # Check for 2XX response code
    r.raise_for_status()

    sleep(0.1)

    return r

def fetch_decklist(decklist_id: str) -> dict:
    return request_emeralddb(f'{API_BASE}/decklists/{decklist_id}').json()

# One bulk request (~2 MB) for every card instead of one request per card
@cache
def fetch_all_cards() -> dict:
    return {card['id']: card for card in request_emeralddb(f'{API_BASE}/cards').json()}

def pick_version(card: dict, pack_id: Optional[str] = None) -> dict:
    versions = [v for v in card.get('versions', []) if v.get('image_url')]
    if not versions:
        raise ValueError(f'No image available for card "{card.get("id")}"')

    # Prefer the printing chosen in the decklist, then a current (non-rotated)
    # printing such as an Emerald Legacy reprint, then whatever is left.
    for version in versions:
        if version.get('pack_id') == pack_id:
            return version
    for version in versions:
        if not version.get('rotated'):
            return version
    return versions[0]

def fetch_card_art(index: int, card_id: str, quantity: int, front_img_dir: str, pack_id: Optional[str] = None) -> None:
    card = fetch_all_cards().get(card_id)
    if card is None:
        raise ValueError(f'Unknown EmeraldDB card "{card_id}"')

    version = pick_version(card, pack_id)

    r = request_emeralddb(version['image_url'])
    if not r.headers.get('content-type', '').startswith('image/'):
        raise ValueError(f'Image URL for "{card_id}" did not return an image: {version["image_url"]}')

    card_art = r.content
    extension = guess_extension(card_art)
    clean_name = sub(r'[^\w]', '', card.get('name') or card_id)

    for counter in range(quantity):
        image_path = path.join(front_img_dir, f'{index}{clean_name}{counter + 1}{extension}')

        with open(image_path, 'wb') as f:
            f.write(card_art)

def get_handle_card(front_img_dir: str):
    def configured_fetch_card(index: int, card_id: str, quantity: int, pack_id: Optional[str] = None):
        fetch_card_art(index, card_id, quantity, front_img_dir, pack_id)

    return configured_fetch_card
