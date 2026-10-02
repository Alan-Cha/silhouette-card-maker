from functools import cache
from os import path
from re import MULTILINE, findall
from requests import Response, Session
from time import sleep

from utilities import guess_extension

session = Session()

CARD_ART_URL_TEMPLATE = 'https://wiki.lotrtcgpc.net/images/LOTR-EN{set}{subset}{card_number:03d}.{version}_card.jpg'

# Gemp's own image overrides for Players Council errata, promos and sets
PC_CARDS_URL = 'https://raw.githubusercontent.com/PlayersCouncil/gemp-lotr/master/gemp-lotr/gemp-lotr-async/src/main/web/js/gemp-022/PC_Cards.js'

def request_lotrtcgpc(query: str) -> Response:
    r = session.get(query, headers = {'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'}, timeout = 30)

    # Check for 2XX response code
    r.raise_for_status()

    # The wiki asks crawlers for a 1 second delay
    sleep(1)

    return r

@cache
def load_pc_card_images() -> dict:
    pc_cards = request_lotrtcgpc(PC_CARDS_URL).text

    # Commented out entries are skipped; later duplicates win, as in JavaScript
    return dict(findall(r"^\s*'(\d+_\d+)'\s*:\s*'([^']+)'", pc_cards, MULTILINE))

def get_card_art_url(blueprint_id: str) -> str:
    # Foil (*) and tengwar (T) versions use the regular image
    blueprint_id = blueprint_id.replace('*', '').replace('T', '')

    pc_card_url = load_pc_card_images().get(blueprint_id)
    if pc_card_url:
        return pc_card_url

    # Otherwise use the same mapping Gemp uses for its deck HTML tooltips
    set_part, card_part = blueprint_id.split('_')
    set_number = int(set_part)
    card_number = int(card_part)

    subset = 'S'
    version = 0
    if 50 <= set_number <= 89:
        # Errata sets: 50-69 and 70-89 re-issue sets 0-19
        set_number -= 50 if set_number <= 69 else 70
        subset = 'E'
        version = 1

    if 100 <= set_number <= 149:
        # Players Council sets V0, V1, ...
        set_name = f'V{set_number - 100}'
    else:
        set_name = f'{set_number:02d}'

    return CARD_ART_URL_TEMPLATE.format(set=set_name, subset=subset, card_number=card_number, version=version)

def fetch_deck_html(deck_url: str) -> str:
    return request_lotrtcgpc(deck_url).text

def fetch_card_art(index: int, image_url: str, quantity: int, front_img_dir: str):
    r = request_lotrtcgpc(image_url)

    # The wiki answers missing images with an HTML page
    if not r.headers.get('content-type', '').startswith('image/'):
        raise ValueError(f'No card image found at {image_url}')

    card_art = r.content
    extension = guess_extension(card_art, '.jpg')
    card_code = path.splitext(path.basename(image_url))[0].removesuffix('_card')

    # Save image based on quantity
    for counter in range(quantity):
        image_path = path.join(front_img_dir, f'{index}{card_code}{counter + 1}{extension}')

        with open(image_path, 'wb') as f:
            f.write(card_art)

def get_handle_card(
    front_img_dir: str
):
    def configured_fetch_card(index: int, image_url: str, quantity: int):
        fetch_card_art(
            index,
            image_url,
            quantity,
            front_img_dir
        )

    return configured_fetch_card
