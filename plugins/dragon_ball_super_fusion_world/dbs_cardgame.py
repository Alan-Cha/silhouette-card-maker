from os import path
from requests import HTTPError, Response, Session
from time import sleep

from utilities import guess_extension

session = Session()

# Regular cards: {code}.webp. Leaders are double-sided: {code}_f.webp / {code}_b.webp.
# Parallels append _p{n}: FB01-004_p1.webp, FB01-001_f_p1.webp.
CARD_ART_URL_TEMPLATE = 'https://www.dbs-cardgame.com/fw/images/cards/card/en/{card_code}{side}{parallel}.webp'

OUTPUT_CARD_ART_FILE_TEMPLATE = '{deck_index}{card_code}{quantity_counter}{extension}'

def request_dbs(query: str) -> Response:
    r = session.get(query, headers = {'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'})

    # Check for 2XX response code
    r.raise_for_status()

    sleep(0.075)

    return r

def card_art_url(card_code: str, side: str = '') -> str:
    base, _, parallel = card_code.partition('_')
    return CARD_ART_URL_TEMPLATE.format(card_code=base, side=side, parallel=f'_{parallel}' if parallel else '')

def write_copies(card_art: bytes, directory: str, index: int, card_code: str, quantity: int):
    extension = guess_extension(card_art)
    for counter in range(quantity):
        image_path = path.join(directory, OUTPUT_CARD_ART_FILE_TEMPLATE.format(deck_index=index, card_code=card_code, quantity_counter=counter + 1, extension=extension))

        with open(image_path, 'wb') as f:
            f.write(card_art)

def fetch_card_art(index: int, card_code: str, quantity: int, front_img_dir: str, double_sided_dir: str):
    # A -F/-B suffix marks a known leader, otherwise a 404 on the plain image means it's a leader
    is_leader = card_code.endswith(('-F', '-B'))
    if is_leader:
        card_code = card_code[:-2]
    else:
        try:
            front = request_dbs(card_art_url(card_code)).content
            back = None
        except HTTPError as e:
            if e.response is None or e.response.status_code != 404:
                raise
            is_leader = True

    if is_leader:
        # Leaders only exist as _f/_b images
        front = request_dbs(card_art_url(card_code, '_f')).content
        back = request_dbs(card_art_url(card_code, '_b')).content

    write_copies(front, front_img_dir, index, card_code, quantity)
    if back is not None:
        write_copies(back, double_sided_dir, index, card_code, quantity)

def get_handle_card(front_img_dir: str, double_sided_dir: str):
    def configured_fetch_card(index: int, card_code: str, quantity: int):
        fetch_card_art(index, card_code, quantity, front_img_dir, double_sided_dir)

    return configured_fetch_card
