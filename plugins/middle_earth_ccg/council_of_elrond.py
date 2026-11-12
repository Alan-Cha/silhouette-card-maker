import os
from functools import lru_cache
from re import sub
from time import sleep
from typing import Tuple
from unicodedata import normalize

import requests

from utilities import guess_extension

CARDS_URL = 'https://raw.githubusercontent.com/council-of-elrond-meccg/meccg-cards-database/master/cards.json'

# Used to pick a printing when a decklist line has no set code: the earliest set wins.
SET_RELEASE_ORDER = ['TW', 'TD', 'DM', 'LE', 'AS', 'WH', 'BA']

session = requests.Session()

def request_council_of_elrond(url: str) -> requests.Response:
    r = session.get(url, headers={'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'}, timeout=30)

    # Check for 2XX response code
    r.raise_for_status()

    sleep(0.075)

    return r

# The whole database is one ~4MB file, fetched once per run.
@lru_cache(maxsize=None)
def fetch_card_database() -> dict:
    return request_council_of_elrond(CARDS_URL).json()

def normalize_name(name: str) -> str:
    # "Thrór’s Map", "Thror's Map" and "thrors map" all match.
    ascii_name = normalize('NFKD', name).encode('ascii', 'ignore').decode()
    return sub(r'[^a-z0-9]', '', ascii_name.lower())

def card_sort_key(card: dict) -> Tuple[int, int]:
    set_rank = SET_RELEASE_ORDER.index(card['set']) if card['set'] in SET_RELEASE_ORDER else len(SET_RELEASE_ORDER)
    return set_rank, int(card['id'].split('-')[1])

def find_card(database: dict, name: str, set_code: str, alignment: str) -> Tuple[dict, dict]:
    """Resolve a decklist entry to (set, card).

    `set_code` (e.g. "TW") and `alignment` (e.g. "H" for Hero, "M" for Minion)
    are optional filters. Among the remaining printings, the earliest set and
    lowest card number wins, so regular prints are preferred over promos. If the
    remaining printings have different alignments, the entry is ambiguous."""
    target = normalize_name(name)

    candidates = [
        (card_set, card)
        for card_set in database.values()
        for card in card_set['cards'].values()
        if normalize_name(card['name']['en']) == target
        and (not set_code or card['set'] == set_code.upper())
        and (not alignment or card['alignment'][0].upper() == alignment[0].upper())
    ]

    if not candidates:
        raise ValueError(f'No card found for "{name}" (set: {set_code or "any"}, alignment: {alignment or "any"})')

    if len({card['alignment'] for _, card in candidates}) > 1:
        options = ', '.join(f'{card["id"]} ({card["alignment"]})' for _, card in candidates)
        raise ValueError(f'"{name}" is ambiguous, add an alignment such as [H] or [M] and a set code such as (TW). Candidates: {options}')

    return min(candidates, key=lambda candidate: card_sort_key(candidate[1]))

def fetch_card_art(
    index: int,
    name: str,
    set_code: str,
    alignment: str,
    quantity: int,
    front_img_dir: str,
    remaster: bool,
) -> None:
    card_set, card = find_card(fetch_card_database(), name, set_code, alignment)

    print(f'Index: {index}, resolved: {card["id"]} {card["name"]["en"]} ({card["alignment"]})')

    image_base_url = card_set['imageBaseUrl']['en' if remaster else 'enOriginal']
    r = request_council_of_elrond(image_base_url + card['image'])

    content_type = r.headers.get('content-type', '')
    if not content_type.startswith('image/'):
        raise ValueError(f'Expected an image for "{card["id"]}" but got "{content_type}"')

    clean_name = sub(r'[^\w]', '', card['name']['en'])
    extension = guess_extension(r.content, '.jpg')

    for counter in range(quantity):
        image_path = os.path.join(front_img_dir, f'{index}{clean_name}{counter + 1}{extension}')

        with open(image_path, 'wb') as f:
            f.write(r.content)

def get_handle_card(front_img_dir: str, remaster: bool):
    def configured_fetch_card(index: int, name: str, set_code: str, alignment: str, quantity: int):
        fetch_card_art(
            index,
            name,
            set_code,
            alignment,
            quantity,
            front_img_dir,
            remaster,
        )

    return configured_fetch_card
