from os import path
from requests import Response, get
from time import sleep

def request_altered(query: str) -> Response:
    r = get(query, headers = {'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'})

    r.raise_for_status()
    sleep(0.15)

    return r

def fetch_card(
    index: int,
    quantity: int,
    qr: str,
    front_img_dir: str,
):

    # Query for card info
    json = request_altered(f'https://api.altered.gg/cards/{qr}').json()
    card_art = request_altered(json.get("imagePath")).content
    
    for counter in range(quantity):
        image_path = path.join(front_img_dir, f'{str(index)}{qr}{str(counter + 1)}.png')

        with open(image_path, 'wb') as f:
            f.write(card_art)

def get_handle_card(
    front_img_dir: str,
):
    def configured_fetch_card(index: int, qr: str, quantity: int = 1):
        fetch_card(
            index,
            quantity,
            qr,
            front_img_dir
        )

    return configured_fetch_card
    