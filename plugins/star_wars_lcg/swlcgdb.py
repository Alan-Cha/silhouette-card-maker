from functools import lru_cache
from io import BytesIO
from os import path
from re import sub
from time import sleep

from PIL import Image
from requests import Response, Session

from utilities import guess_extension

session = Session()

DECK_API_URL_TEMPLATE = 'https://swlcgdb.com/api/decks/{deck_id}'
CARD_BLOCK_API_URL_TEMPLATE = 'https://swlcgdb.com/api/card_blocks/{card_block_id}'
CARD_ART_URL_TEMPLATE = 'https://swlcg-card-images.nyc3.digitaloceanspaces.com/cards/{block}-{block_number}.jpg'

OUTPUT_CARD_ART_FILE_TEMPLATE = '{deck_index}{card_name}{quantity_counter}{extension}'

def request_swlcgdb(query: str) -> Response:
    r = session.get(query, headers = {'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'}, timeout=30)

    # Check for 2XX response code
    r.raise_for_status()

    sleep(0.1)

    return r

def fetch_deck(deck_id: str) -> dict:
    return request_swlcgdb(DECK_API_URL_TEMPLATE.format(deck_id=deck_id)).json()

# Deck entries don't include each card's position within its objective set,
# which the image URL needs, so look it up from the set. Cached because a
# deck has at most 10 distinct objective sets.
@lru_cache(maxsize=None)
def fetch_card_block(card_block_id: int) -> dict:
    return request_swlcgdb(CARD_BLOCK_API_URL_TEMPLATE.format(card_block_id=card_block_id)).json()

def rotate_landscape(image_bytes: bytes) -> bytes:
    img = Image.open(BytesIO(image_bytes))

    # Objective cards are printed landscape but need to be laid out
    # portrait alongside the rest of the deck.
    if img.width <= img.height:
        return image_bytes

    buffer = BytesIO()
    img.rotate(-90, expand=True).save(buffer, format=img.format or 'JPEG')
    return buffer.getvalue()

def fetch_card(
    index: int,
    quantity: int,
    card: dict,
    front_img_dir: str,
):
    card_block = fetch_card_block(card['card_block_id'])
    block_number = next((c['block_number'] for c in card_block.get('cards', []) if c['id'] == card['id']), None)
    if block_number is None:
        raise ValueError(f'Card "{card["name"]}" not found in objective set {card_block.get("block")}')

    r = request_swlcgdb(CARD_ART_URL_TEMPLATE.format(block=card_block['block'], block_number=block_number))
    if not r.headers.get('content-type', '').startswith('image/'):
        raise ValueError(f'No image available for card "{card["name"]}"')

    card_art = rotate_landscape(r.content)
    extension = guess_extension(card_art, '.jpg')
    clean_name = sub(r'[^\w]', '', card['name'])

    # Save image based on quantity
    for counter in range(quantity):
        image_path = path.join(front_img_dir, OUTPUT_CARD_ART_FILE_TEMPLATE.format(deck_index=str(index), card_name=clean_name, quantity_counter=str(counter + 1), extension=extension))

        with open(image_path, 'wb') as f:
            f.write(card_art)

def get_handle_card(
    front_img_dir: str,
):
    def configured_fetch_card(index: int, card: dict, quantity: int = 1):
        fetch_card(
            index,
            quantity,
            card,
            front_img_dir
        )

    return configured_fetch_card
