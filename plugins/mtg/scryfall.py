import os
from typing import List, Set, Tuple
import re
import requests
import time

double_sided_layouts = ['transform', 'modal_dfc']

def request_scryfall(
    query: str,
) -> requests.Response:
    r = requests.get(query, headers = {'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'})

    # Check for 2XX response code
    r.raise_for_status()

    # Sleep for 150 milliseconds, greater than the 100ms requested by Scryfall API documentation
    time.sleep(0.15)

    return r

def fetch_card_art(
    index: int,
    quantity: int,

    clean_card_name: str,
    card_set: int,
    card_collector_number: int,
    layout: str,

    front_img_dir: str,
    double_sided_dir: str
) -> None:
    # Query for the front side
    card_front_image_query = f'https://api.scryfall.com/cards/{card_set}/{card_collector_number}/?format=image&version=png'
    card_art = request_scryfall(card_front_image_query).content
    if card_art is not None:

        # Save image based on quantity
        for counter in range(quantity):
            image_path = os.path.join(front_img_dir, f'{str(index)}{clean_card_name}{str(counter + 1)}.png')

            with open(image_path, 'wb') as f:
                f.write(card_art)

    # Get backside of card, if it exists
    if layout in double_sided_layouts:
        card_back_image_query = f'{card_front_image_query}&face=back'
        card_art = request_scryfall(card_back_image_query).content
        if card_art is not None:

            # Save image based on quantity
            for counter in range(quantity):
                image_path = os.path.join(double_sided_dir, f'{str(index)}{clean_card_name}{str(counter + 1)}.png')

                with open(image_path, 'wb') as f:
                    f.write(card_art)

def remove_nonalphanumeric(s: str) -> str:
    return re.sub(r'[^\w]', '', s)

def partition_printings(printings: List, condition: List) -> Tuple[List, List]:
    matches = []
    non_matches = []
    for card in printings:
        (matches if condition(card) else non_matches).append(card)
    return matches, non_matches

def progressive_filtering(printings: List, filters):
    pool = printings
    leftovers = []

    for condition in filters:
        matched, not_matched = partition_printings(pool, condition)
        leftovers = not_matched + leftovers
        pool = matched or pool  # Only narrow if we have any matches

    return pool + leftovers

def filtering(printings: List, filters):
    pool = printings

    for condition in filters:
        matched, _ = partition_printings(pool, condition)
        pool = matched

    return pool

def fetch_card(
    index: int,
    quantity: int,

    card_set: str,
    card_collector_number: str,
    ignore_set_and_collector_number: bool,

    name: str,

    prefer_older_sets: bool,
    preferred_sets: Set[str],

    prefer_showcase: bool,
    prefer_extra_art: bool,

    front_img_dir: str,
    double_sided_dir: str
):
    if not ignore_set_and_collector_number and card_set != "" and card_collector_number != "":
        card_info_query = f"https://api.scryfall.com/cards/{card_set}/{card_collector_number}"

        # Query for card info
        card_json = request_scryfall(card_info_query).json()

        fetch_card_art(index, quantity, remove_nonalphanumeric(card_json['name']), card_set, card_collector_number, card_json['layout'], front_img_dir, double_sided_dir)

    else:
        if name == "":
            raise Exception()

        # Filter out symbols from card names
        clear_card_name = remove_nonalphanumeric(name)

        card_info_query = f'https://api.scryfall.com/cards/named?exact={clear_card_name}'

        # Query for card info
        card_json = request_scryfall(card_info_query).json()

        set = card_json["set"]
        collector_number = card_json["collector_number"]

        # If preferred options are used, then filter over prints
        if prefer_older_sets or len(preferred_sets) > 0 or prefer_showcase or prefer_extra_art:
            # Get available printings
            prints_search_json = request_scryfall(card_json['prints_search_uri']).json()
            card_printings = prints_search_json['data']

            # Optional reverse for older preferences
            if prefer_older_sets:
                card_printings.reverse()

            # Define filters in order of preference
            filters = [
                lambda c: c['nonfoil'],
                lambda c: not c['digital'],
                lambda c: not c['promo'],
                lambda c: c['set'] in preferred_sets,
                lambda c: not prefer_showcase ^ ('frame_effects' in c and 'showcase' in c['frame_effects']),
                lambda c: not prefer_extra_art ^ (c['full_art'] or c['border_color'] == "borderless" or ('frame_effects' in c and 'extendedart' in c['frame_effects']))
            ]

            # Apply progressive filtering
            filtered_printings = progressive_filtering(card_printings, filters)

            if len(filtered_printings) == 0:
                print(f'No printings found for "{name}" with preferred options. Using default instead.')
            else:
                best_print = filtered_printings[0]
                set = best_print["set"]
                collector_number = best_print["collector_number"]

        # Fetch card art
        fetch_card_art(
            index,
            quantity,
            clear_card_name,
            set,
            collector_number,
            card_json['layout'],
            front_img_dir,
            double_sided_dir
        )

def get_handle_card(
    ignore_set_and_collector_number: bool,

    prefer_older_sets: bool,
    preferred_sets: Set[str],

    prefer_showcase: bool,
    prefer_extra_art: bool,

    front_img_dir: str,
    double_sided_dir: str
):
    def configured_fetch_card(index: int, name: str, card_set: str = None, card_collector_number: int = None, quantity: int = 1):
        fetch_card(
            index,
            quantity,

            card_set,
            card_collector_number,
            ignore_set_and_collector_number,

            name,

            prefer_older_sets,
            preferred_sets,

            prefer_showcase,
            prefer_extra_art,

            front_img_dir,
            double_sided_dir
        )
    return configured_fetch_card