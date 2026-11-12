from io import BytesIO
from os import path
from re import sub
from time import sleep
from urllib.parse import quote

from PIL import Image
from requests import Response, Session

from utilities import guess_extension

session = Session()

# Official English card list images, keyed by the printed card number (e.g. 'WXDi-P01-001[EN]')
CARD_ART_URL_TEMPLATE = 'https://www.takaratomy.co.jp/products/en.wixoss/card/thumb/{card_number}.jpg'

OUTPUT_CARD_ART_FILE_TEMPLATE = '{deck_index}{card_number}{quantity_counter}{extension}'

def request_wixoss(query: str) -> Response:
    r = session.get(query, headers = {'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'}, timeout=30)

    # Check for 2XX response code
    r.raise_for_status()

    sleep(0.2)

    return r

def fetch_deck_page(url: str) -> str:
    return request_wixoss(url).text

def fetch_card(
    index: int,
    quantity: int,
    card_number: str,
    front_img_dir: str,
):
    r = request_wixoss(CARD_ART_URL_TEMPLATE.format(card_number=quote(card_number)))

    if not r.headers.get('content-type', '').startswith('image/'):
        raise ValueError(f'No image available for card "{card_number}"')

    card_art = r.content

    # PIECE cards are printed landscape but need to be laid out portrait alongside the rest of the deck
    img = Image.open(BytesIO(card_art))
    if img.width > img.height:
        buffer = BytesIO()
        img.rotate(-90, expand=True).save(buffer, format=img.format)
        card_art = buffer.getvalue()

    extension = guess_extension(card_art)
    clean_card_number = sub(r'[^\w-]', '', card_number)

    # Save image based on quantity
    for counter in range(quantity):
        image_path = path.join(front_img_dir, OUTPUT_CARD_ART_FILE_TEMPLATE.format(deck_index=str(index), card_number=clean_card_number, quantity_counter=str(counter + 1), extension=extension))

        with open(image_path, 'wb') as f:
            f.write(card_art)

def get_handle_card(
    front_img_dir: str,
):
    def configured_fetch_card(index: int, card_number: str, quantity: int = 1):
        fetch_card(
            index,
            quantity,
            card_number,
            front_img_dir
        )

    return configured_fetch_card
