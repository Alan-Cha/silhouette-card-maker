
import os
import requests
import time

def request_api(query: str) -> requests.Response:
    r = requests.get(query, headers = {'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'})
    r.raise_for_status()
    time.sleep(0.1)

    return r

def fetch_card_art(passcode: int, quantity: int, front_img_dir: str):
    card_front_image_query = f'https://images.ygoprodeck.com/images/cards/{passcode}.jpg'
    card_art = request_api(card_front_image_query).content
    if card_art is not None:

        # Save image based on quantity
        for counter in range(quantity):
            image_path = os.path.join(front_img_dir, f'{passcode}_{counter + 1}.jpg')

            with open(image_path, 'wb') as f:
                f.write(card_art)

            print(f'{image_path}')


# UNUSED. Unable to fetch when using alt art passcodes since db page uses main art passcode
def fetch_card(passcode: int, quantity: int, front_img_dir: str):
        card_info_query = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?id={passcode}"

        # Query for card info
        card_json = request_scryfall(card_info_query).json()[0]
        card_name = card_json['name']
        card_image_url = card_json['']
        fetch_card_art(index, quantity, remove_nonalphanumeric(card_json['name']), card_set, card_collector_number, card_json['layout'], front_img_dir, double_sided_dir)
