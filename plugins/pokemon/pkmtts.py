from os import path
from requests import Session
from requests.exceptions import HTTPError
from time import sleep
import filetype

# PokemonCard.io serves two versions of each card image: a standard PNG and
# a larger, higher-quality JPG (linked as "Image High Res" on card pages).
POKEMONCARD_IO_HIRES_URL_TEMPLATE = 'https://images.pokemoncard.io/images/{set_id}/{set_id}-{card_no}_hiresopt.jpg'
POKEMONCARD_IO_STANDARD_URL_TEMPLATE = 'https://images.pokemoncard.io/images/{set_id}/{set_id}-{card_no}.png'

session = Session()

_failed_hires = set()

def request_pkmtts(url: str):
    r = session.get(url, headers = {'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'})

    # Check for 2XX response code
    r.raise_for_status()

    sleep(0.075)

    return r

def fetch_card(
    index: int,
    quantity: int,
    set_id: str,
    card_number: str,
    front_img_dir: str,
):
    card_art = None

    # Try the hi-res version first
    if set_id not in _failed_hires:
        try:
            url = POKEMONCARD_IO_HIRES_URL_TEMPLATE.format(set_id=set_id, card_no=card_number)
            card_art = request_pkmtts(url).content
        except HTTPError:
            _failed_hires.add(set_id)

    # Fall back to the standard-resolution PNG
    if card_art is None:
        try:
            url = POKEMONCARD_IO_STANDARD_URL_TEMPLATE.format(set_id=set_id, card_no=card_number)
            card_art = request_pkmtts(url).content
        except HTTPError as e:
            raise Exception(f'Failed to fetch card (set: {set_id}, number: {card_number}): {e}')

    file_ext = filetype.guess(card_art).extension

    # pkmtts exports don't include card names, so the filename is just
    # index + copy number, matching limitless.py's index/counter scheme
    # minus the name segment.
    for counter in range(quantity):
        image_path = path.join(front_img_dir, f'{str(index)}{str(counter + 1)}.{file_ext}')

        with open(image_path, 'wb') as f:
            f.write(card_art)

def get_handle_card(
    front_img_dir: str,
):
    def configured_fetch_card(index: int, card_name: str, set_id: str, card_number: str, quantity: int = 1):
        fetch_card(
            index,
            quantity,
            set_id,
            card_number,
            front_img_dir
        )

    return configured_fetch_card
