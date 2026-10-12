from os import path
from requests import Session
from time import sleep
from json import dumps
import re

def remove_nonalphanumeric(s: str) -> str:
    return re.sub(r'[^\w]', '', s)

CURIOSA_API_BASE = 'https://curiosa.io/api/trpc/'

session = Session()
CURIOSA_REFERER = 'https://curiosa.io/'

DECK_ENDPOINTS = [
    'deck.getDecklistById',
    'deck.getAvatarById',
    'deck.getSideboardById',
    'deck.getMaybeboardById',
]

def get_cards(card_result):
    result = card_result.get('result', {}).get('data', {}).get('json', [])
    if isinstance(result, dict):
        return [result]
    return result

def get_curiosa_decklist(deck_id: str):
    deck_id = deck_id.strip()

    api_url = CURIOSA_API_BASE + ','.join(DECK_ENDPOINTS)
    deck_payload = {str(i): {'json': {'id': deck_id}} for i in range(len(DECK_ENDPOINTS))}
    params = {'batch': '1', 'input': dumps(deck_payload)}
    headers = {'referer': CURIOSA_REFERER}

    r = session.get(api_url, params=params, headers=headers)

    # Check for 2XX response code
    r.raise_for_status()

    sleep(0.075)

    decklist = []
    for result in r.json():
        decklist.extend(get_cards(result))

    return decklist

def request_curiosa(url: str):
    r = session.get(url)

    # Check for 2XX response code
    r.raise_for_status()

    sleep(0.075)
    return r

def fetch_card(
    index: int,
    quantity: int,
    card_name: str,
    image_url: str,
    front_img_dir: str,
):
    card_art = request_curiosa(image_url).content
    clean_name = remove_nonalphanumeric(card_name)

    for counter in range(quantity):
        image_path = path.join(front_img_dir, f'{index}{clean_name}{counter + 1}.png')

        with open(image_path, 'wb') as f:
            f.write(card_art)

def get_handle_card(
    front_img_dir: str,
):
    def configured_fetch_card(index: int, card_name: str, image_url: str, quantity: int = 1):
        fetch_card(
            index,
            quantity,
            card_name,
            image_url,
            front_img_dir
        )

    return configured_fetch_card