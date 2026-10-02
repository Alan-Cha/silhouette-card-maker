from functools import cache
from os import path
from time import sleep

from requests import Response, Session

from utilities import guess_extension

session = Session()

# Webula mirrors the card data and card images of the official LackeyCCG Star Trek 2E plugin
WEBULA_BASE_URL = 'https://raw.githubusercontent.com/iftheshoefritz/webula/main/public'
CARD_DATA_URL = f'{WEBULA_BASE_URL}/cards.txt'
CARD_IMAGE_URL_TEMPLATE = WEBULA_BASE_URL + '/cardimages/{image_file}.jpg'

OUTPUT_CARD_ART_FILE_TEMPLATE = '{deck_index}{image_file}{quantity_counter}{extension}'

def request_webula(query: str) -> Response:
    r = session.get(query, headers={'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'}, timeout=30)

    # Check for 2XX response code
    r.raise_for_status()

    sleep(0.075)

    return r

def parse_card_data(card_data_text: str) -> dict:
    # Tab-separated Lackey card data, keyed by both collector info (e.g. "55V027") and Lackey name.
    # The first row wins, so base printings take precedence over alternate printings.
    lines = card_data_text.strip().split('\n')
    header = lines[0].split('\t')
    cards = {}
    for line in lines[1:]:
        row = dict(zip(header, line.rstrip('\r').split('\t')))
        cards.setdefault(row['CollectorsInfo'], row)
        cards.setdefault(row['Name'], row)

    return cards

@cache
def get_card_data() -> dict:
    r = request_webula(CARD_DATA_URL)
    r.encoding = 'utf-8-sig'
    return parse_card_data(r.text)

def fetch_card_image(image_file: str) -> bytes:
    r = request_webula(CARD_IMAGE_URL_TEMPLATE.format(image_file=image_file))
    if not r.headers.get('content-type', '').startswith('image/'):
        raise ValueError(f'Response for "{image_file}" is not an image')

    return r.content

def save_card_image(index: int, image_file: str, card_art: bytes, quantity: int, directory: str) -> None:
    extension = guess_extension(card_art, '.jpg')

    for counter in range(quantity):
        image_path = path.join(directory, OUTPUT_CARD_ART_FILE_TEMPLATE.format(deck_index=str(index), image_file=image_file, quantity_counter=str(counter + 1), extension=extension))

        with open(image_path, 'wb') as f:
            f.write(card_art)

def fetch_card(
    index: int,
    quantity: int,
    card_key: str,
    front_img_dir: str,
    double_sided_dir: str,
):
    card = get_card_data().get(card_key)
    if card is None:
        raise ValueError(f'Card "{card_key}" not found')

    # Double-sided missions list the front and back images separated by a comma
    image_files = card['ImageFile'].split(',')
    save_card_image(index, image_files[0], fetch_card_image(image_files[0]), quantity, front_img_dir)

    if len(image_files) > 1:
        # The back is saved under the front's file name so create_pdf.py pairs them
        save_card_image(index, image_files[0], fetch_card_image(image_files[1]), quantity, double_sided_dir)

def get_handle_card(
    front_img_dir: str,
    double_sided_dir: str,
):
    def configured_fetch_card(index: int, card_key: str, quantity: int = 1):
        fetch_card(
            index,
            quantity,
            card_key,
            front_img_dir,
            double_sided_dir,
        )

    return configured_fetch_card
