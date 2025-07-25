import os
import re
import requests
import time
from io import BytesIO

from PIL import Image

IMAGE_FORMAT = "png"

def request_limitless(
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

def fetch_card_art(set_code: str, collector_number: int) -> Image.Image:
    URL_BASE = f'https://limitlesstcg.nyc3.cdn.digitaloceanspaces.com/tpci'
    URL_END = f'R_EN.{IMAGE_FORMAT}'
    
    image_query = f'{URL_BASE}/{set_code}/{set_code}_{collector_number:03d}_{URL_END}'
    return Image.open(BytesIO(request_limitless(image_query).content))
    
def fetch_card(
    index: int,
    quantity: int,

    card_set: str,
    card_collection_number: int,
    name: str,

    front_img_dir: str
) -> None:

    clean_card_name = remove_nonalphanumeric(name)
    card_art = fetch_card_art(card_set, card_collection_number)

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