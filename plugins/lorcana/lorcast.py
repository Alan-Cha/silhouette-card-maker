import csv
import os
from typing import List, Set, Tuple
import re
import requests
import time

def request_lorcast(
    query: str,
) -> requests.Response:
    r = requests.get(query, headers = {'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'})

    # Check for 2XX response code
    r.raise_for_status()

    # Sleep for 150 milliseconds, greater than the 100ms requested by scryfall API documentation
    time.sleep(0.1)

    return r

def format_lorcast_query(name: str, enchanted: bool) -> str:
    return re.sub(r'[^\w]', '+', name) + "+" + enchanted*"rarity:enchanted"

def remove_nonalphanumeric(s: str) -> str:
    return re.sub(r'[^\w]', '', s)

def fetch_card(
    index: int,
    quantity: int,

    #card_set: str,
    #card_collector_number: str,
    #ignore_set_and_collector_number: bool,

    name: str,
    enchanted: bool,

    #prefer_older_sets: bool,
    #preferred_sets: Set[str],

    #prefer_showcase: bool,
    #prefer_extra_art: bool,

    front_img_dir: str,
    double_sided_dir: str
):

    if name == "":
        raise Exception()

    # Filter out symbols from card names
    clean_card_name = remove_nonalphanumeric(name)
    card_query = format_lorcast_query(name, enchanted)

    card_info_query = f'https://api.lorcast.com/v0/cards/search?q={card_query}'

    # Query for card info
    card_json = request_lorcast(card_info_query).json()['results'][0]

    card_set = card_json["set"]["code"]
    collector_number = card_json["collector_number"]

    card_front_image_url = card_json['image_uris']['digital']['large']
    card_art = request_lorcast(card_front_image_url).content

    if card_art is not None:
        # Save image based on quantity
        for counter in range(quantity):
            image_path = os.path.join(front_img_dir, f'{str(index)}{clean_card_name}{str(counter + 1)}.avif')

            with open(image_path, 'wb') as f:
                f.write(card_art)


def get_handle_card(
    #ignore_set_and_collector_number: bool,

    #prefer_older_sets: bool,
    #preferred_sets: Set[str],

    #prefer_showcase: bool,
    #prefer_extra_art: bool,

    front_img_dir: str,
    double_sided_dir: str
):
    def configured_fetch_card(index: int, name: str, enchanted: bool, quantity: int = 1):
        fetch_card(
            index,
            quantity,

            #card_set,
            #card_collector_number,
            #ignore_set_and_collector_number,

            name,
            enchanted,

            #prefer_older_sets,
            #preferred_sets,

            #prefer_showcase,
            #prefer_extra_art,

            front_img_dir,
            double_sided_dir
        )

    return configured_fetch_card