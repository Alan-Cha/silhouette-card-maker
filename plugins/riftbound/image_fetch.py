from os import path
from requests import Response, get, HTTPError
from time import sleep
from re import compile, search
from typing import Tuple
from enum import Enum

response_tuple = Tuple[bool, Response]

class ImageServer(str, Enum):
    PILTOVER = "piltover_archive"
    RIFTMANA = "riftmana" 

def request_api(query: str) -> response_tuple:
    r = get(query, headers = {'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'})

    try:
        r.raise_for_status()
        sleep(0.15)
    except HTTPError:
        return (False, r)

    return (True, r)

def fetch_card_art(card_number: str, quantity: int, image_server: ImageServer, front_img_dir: str):
    alternate_art_suffix_pattern = compile(r'^(\D{3}-\d{3})a$')
    signed_art_suffix = 's'

    image_server_query = lambda image_server : f'https://riftmana.com/wp-content/uploads/Cards/{card_number}.webp' if image_server == ImageServer.RIFTMANA else f'https://piltoverarchive.com/_next/image?url=https%3A%2F%2Fcdn.piltoverarchive.com%2Fcards%2F{card_number}.webp&w=1920&q=75'
    success, api_response = request_api(image_server_query(image_server))
    card_art = api_response.content
    
    if success and card_art is not None: # Try to use the base/alternate art of the card
        # Save image based on quantity
        for counter in range(quantity):
            image_path = path.join(front_img_dir, f'{card_number}_{counter + 1}.jpg')

            with open(image_path, 'wb') as f:
                f.write(card_art)

            print(f'{image_path}')
    else: # Otherwise, try to retrieve the art for the signature art of the card since the request failed for alternate art
        match = search(alternate_art_suffix_pattern, card_number)
        if match:
            fetch_card_art(f'{match.group(1)}{signed_art_suffix}', quantity, front_img_dir)