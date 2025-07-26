from os import path
from re import compile, search
from enum import Enum

from api import request_api

class ImageServer(str, Enum):
    PILTOVER = 'piltover_archive'
    RIFTMANA = 'riftmana'

def fetch_card_art(index: int, card_number: str, quantity: int, image_server: ImageServer, front_img_dir: str):
    alternate_art_suffix_pattern = compile(r'^([A-Z0-9]+-\d+)a$')
    signed_art_suffix = 's'

    image_server_query = lambda image_server : f'https://riftmana.com/wp-content/uploads/Cards/{card_number}.webp' if image_server == ImageServer.RIFTMANA else f'https://piltoverarchive.com/_next/image?url=https://cdn.piltoverarchive.com/cards/{card_number}.webp&w=1920&q=75'
    success, api_response = request_api(image_server_query(image_server))
    card_art = api_response.content
    
    if success and card_art is not None: # Try to use the base/alternate art of the card
        # Save image based on quantity
        for counter in range(quantity):
            image_path = path.join(front_img_dir, f'{index}{card_number}_{counter + 1}.jpg')

            with open(image_path, 'wb') as f:
                f.write(card_art)

            print(f'{image_path}')
    else: # Otherwise, try to retrieve the art for the signature art of the card since the request failed for alternate art
        match = search(alternate_art_suffix_pattern, card_number)
        if match:
            fetch_card_art(index, f'{match.group(1)}{signed_art_suffix}', quantity, image_server, front_img_dir)