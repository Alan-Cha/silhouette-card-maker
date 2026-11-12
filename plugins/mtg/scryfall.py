import os
from io import BytesIO
from typing import List, Optional, Tuple
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import requests
import time

from PIL import Image

from .common import remove_nonalphanumeric, ScryfallLanguage, to_scryfall_api_lang

double_sided_layouts = ['transform', 'modal_dfc', 'double_faced_token', 'reversible_card', 'meld']

session = requests.Session()

def append_search_filter(uri: str, filter_term: str) -> str:
    parsed = urlparse(uri)
    params = parse_qs(parsed.query, keep_blank_values=True)
    q_val = params.get('q', [''])[0]
    params['q'] = [q_val + ' ' + filter_term]
    return urlunparse(parsed._replace(query=urlencode(params, doseq=True)))

def fetch_printings(prints_search_uri: str, prefer_ub: Optional[bool], name: str) -> List:
    if prefer_ub is not None:
        filter_term = 'is:ub' if prefer_ub else '-is:ub'
        filtered_uri = append_search_filter(prints_search_uri, filter_term)
        try:
            filtered = request_scryfall(filtered_uri).json().get('data', [])
        except requests.exceptions.HTTPError:
            filtered = []
        if filtered:
            return filtered
        label = 'No Universe Beyond' if prefer_ub else 'All'
        flag = '--prefer_ub' if prefer_ub else '--ignore_ub'
        print(f'{label} printings for "{name}" are Universe Beyond. Ignoring {flag}.')
    return request_scryfall(prints_search_uri).json()['data']

def request_scryfall(
    query: str,
    params: dict = None,
    retry_count: int = 0,
) -> requests.Response:
    r = session.get(query, params=params, headers = {'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'})

    # Rate limit check - Scryfall requires 30 second wait per their documentation
    if r.status_code == 429:
        if retry_count >= 3:
            print(f"Warning: Hit rate limit 3 times for {query}, giving up after 30s wait")
            raise requests.exceptions.HTTPError(f"Max retries (3) exceeded for Scryfall API: {query}", response=r)
        print(f"Hit Scryfall rate limit (429), waiting 30 seconds before retry {retry_count + 1}/3...")
        time.sleep(30)
        return request_scryfall(query, params, retry_count + 1)

    r.raise_for_status()

    # Apply rate limiting per Scryfall API documentation
    # See: https://scryfall.com/docs/api/rate-limits
    # Note: Direct image downloads from *.scryfall.io CDN have NO rate limits

    if "cards/search" in query or "cards/named" in query:
        time.sleep(0.5)   # Search/named endpoints: 2 requests/second (500ms delay)
    elif 'api.scryfall.com' in query:
        time.sleep(0.1)  # All other API methods: 10 requests/second (100ms delay)
    # else: No rate limiting needed for direct image downloads from *.scryfall.io CDN

    return r

def save_card_art_copies(data: bytes, output_dir: str, index: int, clean_card_name: str, quantity: int) -> None:
    for counter in range(quantity):
        image_path = os.path.join(output_dir, f'{index}{clean_card_name}{counter + 1}.png')
        with open(image_path, 'wb') as f:
            f.write(data)

def fetch_meld_back(
    index: int,
    quantity: int,

    clean_card_name: str,
    card_name: str,
    all_parts: List,

    double_sided_dir: str
) -> None:
    meld_result = None
    meld_parts = []
    for part in all_parts:
        if part['component'] == 'meld_result':
            meld_result = part
        elif part['component'] == 'meld_part':
            meld_parts.append(part)

    if meld_result is None or len(meld_parts) != 2:
        return

    # Don't fetch back if this card is the meld result itself
    if meld_result['name'] == card_name:
        return

    # Find the 0-based index of this card within meld_parts (the two non-result halves).
    # Scryfall lists meld parts in a consistent order; index 0 = top half, index 1 = bottom half.
    # next() returns the first index i where the part's name matches, or -1 as the default.
    meld_part_index = next((i for i, p in enumerate(meld_parts) if p['name'] == card_name), -1)
    if meld_part_index == -1:
        return

    # Fetch the meld result card info; the PNG URL is in the response, no second request needed
    meld_result_json = request_scryfall(meld_result['uri']).json()
    meld_result_image_data = request_scryfall(meld_result_json['image_uris']['png']).content

    # Split the meld result image into top/bottom halves
    img = Image.open(BytesIO(meld_result_image_data))
    width, height = img.size
    half_height = height // 2

    # Scryfall lists meld parts by collector number; index 0 is the lower-numbered card,
    # which corresponds to the bottom half of the combined image.
    if meld_part_index == 0:
        cropped = img.crop((0, half_height, width, height))  # bottom half
    else:
        cropped = img.crop((0, 0, width, half_height))  # top half

    # Rotate 90° clockwise (meld result images are stored upright)
    cropped = cropped.rotate(-90, expand=True)

    # Resize to full card dimensions
    resized = cropped.resize((width, height), Image.LANCZOS)

    # Save image based on quantity
    for counter in range(quantity):
        image_path = os.path.join(double_sided_dir, f'{str(index)}{clean_card_name}{str(counter + 1)}.png')
        resized.save(image_path)

def build_image_url(card_set: str, card_collector_number: str, prefer_lang: ScryfallLanguage = None) -> str:
    if prefer_lang and prefer_lang != ScryfallLanguage.ENGLISH:
        api_lang = to_scryfall_api_lang(prefer_lang)
        return f'https://api.scryfall.com/cards/{card_set}/{card_collector_number}/{api_lang}?format=image&version=png'
    return f'https://api.scryfall.com/cards/{card_set}/{card_collector_number}/?format=image&version=png'

def fetch_image(card_set: str, card_collector_number: str, prefer_langs: List[ScryfallLanguage] = None, face: str = None) -> bytes:
    langs_to_try = list(prefer_langs) if prefer_langs else []
    if not langs_to_try or langs_to_try[-1] != ScryfallLanguage.ENGLISH:
        langs_to_try.append(ScryfallLanguage.ENGLISH)

    last_error = None
    for i, lang in enumerate(langs_to_try):
        url = build_image_url(card_set, card_collector_number, lang)
        if face:
            url = f'{url}&face={face}'
        try:
            return request_scryfall(url).content
        except requests.exceptions.HTTPError as e:
            if e.response is None or e.response.status_code != 404:
                raise
            last_error = e
            if i < len(langs_to_try) - 1:
                next_lang = langs_to_try[i + 1]
                print(f'Language "{lang.value}" not available for set code: {card_set} and collector number: {card_collector_number}, falling back to "{next_lang.value}".')
    raise last_error

def fetch_card_art(
    index: int,
    quantity: int,

    clean_card_name: str,
    card_set: str,
    card_collector_number: str,
    output_dir: str,

    prefer_langs: List[ScryfallLanguage] = None,
    face: str = None,
) -> None:
    card_art = fetch_image(card_set, card_collector_number, prefer_langs, face=face)
    if card_art is not None:
        save_card_art_copies(card_art, output_dir, index, clean_card_name, quantity)

def fetch_card_faces(
    index: int,
    quantity: int,

    clean_card_name: str,
    card_set: str,
    card_collector_number: str,
    layout: str,

    prefer_langs: List[ScryfallLanguage] = None,

    front_img_dir: str = None,
    double_sided_dir: str = None,

    all_parts: List = None,
    card_name: str = None,
) -> None:
    # Front face
    fetch_card_art(index, quantity, clean_card_name, card_set, card_collector_number, front_img_dir, prefer_langs)

    # Get backside of card, if it exists
    if layout in double_sided_layouts:
        if layout == 'meld':
            if all_parts and card_name:
                fetch_meld_back(index, quantity, clean_card_name, card_name, all_parts, double_sided_dir)
        else:
            fetch_card_art(index, quantity, clean_card_name, card_set, card_collector_number, double_sided_dir, prefer_langs, face='back')

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
    prefer_sets: List[str],
    ignore_sets: List[str],

    prefer_showcase: bool,
    prefer_extra_art: bool,
    prefer_ub: bool,
    ignore_ub: bool,

    prefer_langs: List[ScryfallLanguage],

    tokens: bool,

    front_img_dir: str,
    double_sided_dir: str,
):
    # Query based on card set and card collector number if provided
    if not ignore_set_and_collector_number and card_set != "" and card_collector_number != "":
        card_info_query = f"https://api.scryfall.com/cards/{card_set.lower()}/{card_collector_number}"

        # Query for card info
        card_json = request_scryfall(card_info_query).json()

        fetch_card_faces(
            index,
            quantity,
            remove_nonalphanumeric(card_json['name']),
            card_json['set'],
            card_json['collector_number'],
            card_json['layout'],
            prefer_langs,
            front_img_dir,
            double_sided_dir,
            card_json.get('all_parts'),
            card_json['name'],
        )

        # Fetch tokens
        if tokens:
            if all_parts := card_json.get("all_parts"):
                for related in all_parts:
                    if related["component"] == "token":
                        card_info_query = related["uri"]
                        card_json = request_scryfall(card_info_query).json()
                        fetch_card_faces(
                            index,
                            quantity,
                            # Offsprint tokens have the same name as the card, so append _token to differentiate
                            f'{remove_nonalphanumeric(related["name"])}_token',
                            card_json["set"],
                            card_json["collector_number"],
                            card_json["layout"],
                            prefer_langs=prefer_langs,
                            front_img_dir=front_img_dir,
                            double_sided_dir=double_sided_dir,
                        )

    # Query based on card name
    else:
        if name == "":
            raise Exception()

        # Query for card info (use params= for correct URL encoding of accented/special chars)
        try:
            card_json = request_scryfall('https://api.scryfall.com/cards/named', params={'exact': name}).json()
        except requests.exceptions.HTTPError as e:
            if e.response is None or e.response.status_code != 404:
                raise
            # Fall back to flavor name search (e.g. Godzilla series, convention promos)
            search_json = request_scryfall('https://api.scryfall.com/cards/search', params={'q': f'flavor_name:"{name}"', 'unique': 'cards'}).json()
            if not search_json.get('data'):
                raise
            card_json = search_json['data'][0]
            print(f'Found by flavor name: {card_json["name"]}')

        # Filter out symbols from card names for use in filenames
        clean_card_name = remove_nonalphanumeric(name)

        set = card_json["set"]
        collector_number = card_json["collector_number"]

        # Filter over available printings when any filtering option is set
        needs_filtering = prefer_langs or prefer_older_sets or prefer_sets or ignore_sets or prefer_showcase or prefer_extra_art or prefer_ub or ignore_ub
        if needs_filtering:
            ub_preference = True if prefer_ub else (False if ignore_ub else None)
            card_printings = fetch_printings(card_json['prints_search_uri'], ub_preference, name)

            if ignore_sets:
                remaining = [c for c in card_printings if c['set'] not in ignore_sets]
                if not remaining:
                    print(f'All printings for "{name}" are in ignored sets. Ignoring --ignore_set.')
                else:
                    card_printings = remaining

            if prefer_older_sets:
                card_printings.reverse()

            # Define filters in order of preference.
            # Language filters are applied FIRST to ensure we only consider printings available in the preferred language.
            # This prevents situations where full-art/showcase versions are selected but only available in English.
            # prefer_langs is an ordered list: each language gets its own filter so earlier languages rank higher.
            # prefer_sets is an ordered list: each set gets its own filter so earlier sets rank higher.
            filters = [
                *[lambda c, lang=lang: c['lang'] == to_scryfall_api_lang(lang) for lang in prefer_langs or []],
                lambda c: c['nonfoil'],
                lambda c: not c['digital'],
                lambda c: not c['promo'],
                *[lambda c, s=s: c['set'] == s for s in prefer_sets],
                lambda c: not prefer_showcase ^ ('frame_effects' in c and 'showcase' in c['frame_effects']),
                lambda c: not prefer_extra_art ^ (c['full_art'] or c['border_color'] == "borderless" or ('frame_effects' in c and 'extendedart' in c['frame_effects']))
            ]

            filtered_printings = progressive_filtering(card_printings, filters)

            if len(filtered_printings) == 0:
                print(f'No printings found for "{name}" with preferred options. Using default instead.')
            else:
                best_print = filtered_printings[0]
                set = best_print["set"]
                collector_number = best_print["collector_number"]

        fetch_card_faces(
            index,
            quantity,
            clean_card_name,
            set,
            collector_number,
            card_json['layout'],
            prefer_langs,
            front_img_dir,
            double_sided_dir,
            card_json.get('all_parts'),
            card_json['name'],
        )

        # Fetch tokens
        if tokens:
            if all_parts := card_json.get("all_parts"):
                for related in all_parts:
                    if related["component"] == "token":
                        card_info_query = related["uri"]
                        card_json = request_scryfall(card_info_query).json()
                        fetch_card_faces(
                            index,
                            quantity,
                            # Offsprint tokens have the same name as the card, so append _token to differentiate
                            f'{remove_nonalphanumeric(related["name"])}_token',
                            card_json["set"],
                            card_json["collector_number"],
                            card_json["layout"],
                            prefer_langs=prefer_langs,
                            front_img_dir=front_img_dir,
                            double_sided_dir=double_sided_dir,
                        )

def get_handle_card(
    ignore_set_and_collector_number: bool,

    prefer_older_sets: bool,
    prefer_sets: List[str],
    ignore_sets: List[str],

    prefer_showcase: bool,
    prefer_extra_art: bool,
    prefer_ub: bool,
    ignore_ub: bool,

    prefer_langs: List[ScryfallLanguage],

    tokens: bool,

    front_img_dir: str,
    double_sided_dir: str,
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
            prefer_sets,
            ignore_sets,

            prefer_showcase,
            prefer_extra_art,
            prefer_ub,
            ignore_ub,

            prefer_langs,

            tokens,

            front_img_dir,
            double_sided_dir,
        )
    return configured_fetch_card
