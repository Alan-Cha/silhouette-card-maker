from os import path
from requests import Response, get, post
from time import sleep
from typing import Tuple

AIDALONDB_DECK_URL_TEMPLATE = 'https://api.aidalon-db.com/api/decks/get?id={deck_code}'
AIDALONDB_CARDID_URL = 'https://api.aidalon-db.com/api/cards/byIds'

CARD_ART_TUPLE = Tuple[str, str] # Front Art, Back Art

def get_aidalondb_decks(deck_text: str):
    cards = []
    for deck_id in deck_text.strip().split('\n'):
        resp = get(AIDALONDB_DECK_URL_TEMPLATE.format(deck_code=deck_id), headers={'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'})
        resp.raise_for_status()
        data = resp.json()
        cards.extend(data.get('cards', []))
    return cards

def get_card_art(card_id: str) -> str:
    card_params = [card_id]
    r = post(AIDALONDB_CARDID_URL, json=card_params, headers = {'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'})

    r.raise_for_status()
    data = r.json()

    front_art = data[0].get('imageUrl', {}).get('url', None)
    back_art = (data[0].get('backImageUrl') or {}).get('url', None)

    return (front_art, back_art)


def request_art(query: str) -> Response:

    r = get(query, headers = {'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'})

    r.raise_for_status()
    sleep(0.15)

    return r

def fetch_card(
    index: int,
    quantity: int,
    card_id: str,
    front_img_dir: str,
    back_img_dir: str,
):
    # Query for card info
    front_art_url, back_art_url = get_card_art(card_id)
    front_card_art = request_art(front_art_url).content if front_art_url is not None else None
    back_card_art = request_art(back_art_url).content if back_art_url is not None else None

    for counter in range(quantity):
        if front_card_art is not None:
            front_image_path = path.join(front_img_dir, f'{str(index)}_{card_id}_{str(counter + 1)}.png')

            with open(front_image_path, 'wb') as ff:
                ff.write(front_card_art)

        if back_card_art is not None:
            back_image_path = path.join(back_img_dir, f'{str(index)}_{card_id}_{str(counter + 1)}.png')

            with open(back_image_path, 'wb') as bf:
                bf.write(back_card_art)

def get_handle_card(
    front_img_dir: str,
    back_img_dir: str,
):
    def configured_fetch_card(index: int, card_id: str, quantity: int = 1):
        fetch_card(
            index,
            quantity,
            card_id,
            front_img_dir,
            back_img_dir
        )

    return configured_fetch_card