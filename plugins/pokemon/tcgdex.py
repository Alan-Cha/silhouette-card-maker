# TCGdex uses some custom set id that doesn't match up with the decklist export format
# If there was a way to link these set IDs, this would be usable.

import os
import re
import requests
import time
from io import BytesIO

from PIL import Image

API_ENDPOINT = "https://api.tcgdex.net/v2/en/cards"
IMAGE_FORMAT = "png"

def request_tcgdex(
    query: str,
) -> requests.Response:
    r = requests.get(query, headers = {'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'})

    # Check for 2XX response code
    r.raise_for_status()

    # Sleep for 150 milliseconds, greater than the 100ms requested by Scryfall API documentation
    time.sleep(0.1)

    return r

def remove_nonalphanumeric(s: str) -> str:
    return re.sub(r'[^\w]', '', s)

def fetch_card_art(image_url: str) -> Image.Image:
    IMAGE_QUALITY = 'high'

    image_query = f'{image_url}/{IMAGE_QUALITY}.{IMAGE_FORMAT}'
    return Image.open(BytesIO(request_tcgdex(image_query).content))
    
def fetch_card(
    index: int,
    quantity: int,

    card_set: str,
    card_collection_number: int,
    name: str,

    front_img_dir: str
) -> None:

    clean_card_name = remove_nonalphanumeric(name)
    card_query = f'{API_ENDPOINT}/{card_set}-{card_collection_number}'
    card_json = request_tcgdex(card_query).json()
    card_art = fetch_card_art(card_json['image'])

    if card_art is not None:
        for i in range(quantity):
            image_path = os.path.join(front_img_dir, f'{str(index)}{clean_card_name}{str(i + 1)}.{IMAGE_FORMAT}')
            card_art.save(image_path, format=IMAGE_FORMAT)

def get_handle_card(
    front_img_dir: str
):
    def configured_fetch_card(
        index: int, 
        name: str, 
        card_set: str = None, 
        card_collector_number: int = None, 
        quantity: int = 1):

        fetch_card(
            index,
            quantity,

            card_set,
            card_collector_number,
            name,
            front_img_dir
        )
    return configured_fetch_card