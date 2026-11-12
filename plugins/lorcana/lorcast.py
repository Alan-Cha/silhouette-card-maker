import os
import re
import requests
import time
from io import BytesIO
from typing import Optional

from PIL import Image

from plugins.lorcana.common import remove_nonalphanumeric

session = requests.Session()

_promo_set_codes_cache: Optional[list] = None

def request_lorcast(
    query: str,
) -> requests.Response:
    r = session.get(query, headers = {'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'})

    # Check for 2XX response code
    r.raise_for_status()

    # Sleep for 75 ms, greater than the 50 ms requested by Lorcast API documentation
    # See rate limits: https://lorcast.com/docs/api
    time.sleep(0.075)

    return r

def get_promo_set_codes() -> list:
    # Lorcast's `rarity:` search filter does not recognize "promo" as a value,
    # even though "Promo" is a real rarity in the card data. To find promo
    # printings, look up sets whose code isn't a normal numbered set (e.g.
    # "P1", "cp", "D23") since promo cards are only printed in those sets.
    # The result is cached since sets rarely change within a single run.
    global _promo_set_codes_cache

    if _promo_set_codes_cache is None:
        sets_json = request_lorcast('https://api.lorcast.com/v0/sets').json()['results']
        # Normal (non-promo) sets are expected to have a purely numerical set code.
        _promo_set_codes_cache = [s['code'] for s in sets_json if not s['code'].isdigit()]

    return _promo_set_codes_cache

def format_lorcast_query(name: str, variant: Optional[str]) -> str:
    query = re.sub(r'[^\w]', '+', name)

    if variant == 'promo':
        promo_set_codes = get_promo_set_codes()
        if not promo_set_codes:
            raise ValueError('No promo set codes found from Lorcast API')
        set_clause = '+or+'.join(f'set:{code}' for code in promo_set_codes)
        query += f'+({set_clause})'
    elif variant and variant.startswith('set:'):
        # A specific print marker (e.g. "set:P2 cn:15") built by
        # deck_formats.py to select an exact printing - append it as-is.
        query += '+' + variant.replace(' ', '+')
    elif variant:
        query += f'+rarity:{variant}'

    return query

def fetch_card(
    index: int,
    quantity: int,
    name: str,
    variant: Optional[str],
    front_img_dir: str,
):
    # Filter out symbols from card names
    clean_card_name = remove_nonalphanumeric(name)
    card_query = format_lorcast_query(name, variant)

    card_info_query = f'https://api.lorcast.com/v0/cards/search?q={card_query}'

    # Query for card info
    card_json = request_lorcast(card_info_query).json()['results'][0]

    image_uris = card_json['image_uris']['digital']
    
    card_front_image_url = ''
    if 'large' in image_uris:
        card_front_image_url = image_uris['large']
    elif 'medium' in image_uris:
        card_front_image_url = image_uris['medium']
    elif 'small' in image_uris:
        card_front_image_url = image_uris['small']
    else:
        raise Exception(f'No images available for "{name}"')

    card_art = Image.open(BytesIO(request_lorcast(card_front_image_url).content))

    if card_art is not None:
        # Save image based on quantity
        for counter in range(quantity):
            image_path = os.path.join(front_img_dir, f'{str(index)}{clean_card_name}{str(counter + 1)}.png')

            card_art.save(image_path, format="PNG")

def get_handle_card(
    front_img_dir: str,
):
    def configured_fetch_card(index: int, name: str, variant: Optional[str], quantity: int = 1):
        fetch_card(
            index,
            quantity,
            name,
            variant,
            front_img_dir,
        )

    return configured_fetch_card