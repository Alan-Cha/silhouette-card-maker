from os import path
from requests import Session
from time import sleep
from json import dumps
from PIL import Image
import re

def remove_nonalphanumeric(s: str) -> str:
    return re.sub(r'[^\w]', '', s)

# Curiosa moved to sorcerytcg.com. curiosa.io now redirects there, and deck IDs are unchanged.
SORCERY_API_BASE = 'https://sorcerytcg.com/api/trpc/'
SORCERY_REFERER = 'https://sorcerytcg.com/'

DECK_ENDPOINT = 'deck.get'

session = Session()

def get_curiosa_decklist(deck_id: str):
    deck_id = deck_id.strip()

    api_url = SORCERY_API_BASE + DECK_ENDPOINT
    deck_payload = {'0': {'json': {'id': deck_id}}}
    params = {'batch': '1', 'input': dumps(deck_payload)}
    headers = {'referer': SORCERY_REFERER}

    r = session.get(api_url, params=params, headers=headers)

    sleep(0.075)

    if r.status_code == 404:
        print(f'Deck "{deck_id}" was not found. Make sure that the deck is public.')
        return []

    # Check for 2XX response code
    r.raise_for_status()

    deck = r.json()[0].get('result', {}).get('data', {}).get('json', {})
    return deck.get('decklist', [])

def request_curiosa(url: str):
    r = session.get(url)

    # Check for 2XX response code
    r.raise_for_status()

    sleep(0.075)
    return r

def save_atlas_back(atlas_back_path: str, image_path: str):
    # Card images serve Sites in portrait orientation, so turn a landscape atlas back to match
    with Image.open(atlas_back_path) as atlas_back:
        if atlas_back.width > atlas_back.height:
            atlas_back = atlas_back.rotate(-90, expand=True)
        atlas_back.save(image_path, format='PNG')

def fetch_card(
    index: int,
    quantity: int,
    card_name: str,
    image_url: str,
    is_site: bool,
    front_img_dir: str,
    double_sided_dir: str,
    atlas_back_path: str | None,
):
    card_art = request_curiosa(image_url).content
    clean_name = remove_nonalphanumeric(card_name)

    for counter in range(quantity):
        image_name = f'{index}{clean_name}{counter + 1}.png'
        image_path = path.join(front_img_dir, image_name)

        with open(image_path, 'wb') as f:
            f.write(card_art)

        if is_site and atlas_back_path is not None and double_sided_dir is not None:
            save_atlas_back(atlas_back_path, path.join(double_sided_dir, image_name))

def get_handle_card(
    front_img_dir: str,
    double_sided_dir: str | None = None,
    atlas_back_path: str | None = None,
):
    def configured_fetch_card(index: int, card_name: str, image_url: str, quantity: int = 1, is_site: bool = False):
        fetch_card(
            index,
            quantity,
            card_name,
            image_url,
            is_site,
            front_img_dir,
            double_sided_dir,
            atlas_back_path,
        )

    return configured_fetch_card
