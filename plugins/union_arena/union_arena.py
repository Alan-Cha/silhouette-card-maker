from os import path
from re import sub, IGNORECASE
from requests import HTTPError, Response, Session
from time import sleep

from utilities import guess_extension

session = Session()

# Official card list image path; the '/' in a card number becomes '_',
# e.g. UE03BT/JJK-1-001 -> UE03BT_JJK-1-001.png (parallels add a '_p1' suffix).
# Regions: 'na' (English, UE... cards), 'en' (Asia English, UA/EX/PC... cards), 'jp' (Japanese, all UA... cards incl. promos).
CARD_ART_URL_TEMPLATE = 'https://www.unionarena-tcg.com/{region}/images/cardlist/card/{image_id}.png'

OUTPUT_CARD_ART_FILE_TEMPLATE = '{deck_index}{image_id}{quantity_counter}{extension}'

def request_bandai(query: str) -> Response:
    r = session.get(query, headers = {'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'})

    # Check for 2XX response code
    r.raise_for_status()

    sleep(0.075)

    return r

def card_image_id(card_number: str) -> str:
    if '/' not in card_number:
        raise ValueError(f'Card number {card_number} is missing its set prefix. Use the full card number printed on the card, such as UE03BT/JJK-1-001.')

    # ExBurst alternate art IDs ('-ALT1') are the official parallel suffix ('_p1')
    return sub(r'-ALT(\d+)$', r'_p\1', card_number, flags=IGNORECASE).replace('/', '_')

def card_regions(image_id: str) -> tuple:
    # UE... cards are only on the North American site; Asia cards fall back to Japanese when not on the Asia English site
    return ('na',) if image_id.upper().startswith('UE') else ('en', 'jp')

def fetch_card(
    index: int,
    quantity: int,
    card_number: str,
    front_img_dir: str,
):
    image_id = card_image_id(card_number)
    regions = card_regions(image_id)
    for region in regions:
        try:
            response = request_bandai(CARD_ART_URL_TEMPLATE.format(region=region, image_id=image_id))
            break
        except HTTPError as e:
            if e.response.status_code != 404 or region == regions[-1]:
                raise

    content_type = response.headers.get('content-type', '')
    if not content_type.startswith('image/'):
        raise ValueError(f'Expected an image for {card_number}, got "{content_type}"')

    card_art = response.content
    extension = guess_extension(card_art)

    # Save image based on quantity
    for counter in range(quantity):
        image_path = path.join(front_img_dir, OUTPUT_CARD_ART_FILE_TEMPLATE.format(deck_index=str(index), image_id=image_id, quantity_counter=str(counter + 1), extension=extension))

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
