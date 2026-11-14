import logging
import os
import re
import time
from io import BytesIO
from typing import Optional

import requests
from PIL import Image

from plugins.lorcana.common import remove_nonalphanumeric
from utilities import guess_extension

logger = logging.getLogger(__name__)

# API Constants
LORCAST_API_URL = "https://api.lorcast.com/v0/cards/search"
LORCAST_SETS_URL = "https://api.lorcast.com/v0/sets"

# Request timeout in seconds
REQUEST_TIMEOUT = 30

# Rate limiting sleep in seconds
# Sleep for 75 ms, greater than the 50 ms requested by Lorcast API documentation
# See rate limits: https://lorcast.com/docs/api
RATE_LIMIT_SLEEP = 0.075

session = requests.Session()

# Cache for the promo set codes, since sets rarely change within a single run
_promo_set_codes_cache: Optional[list] = None


def request_lorcast(query: str) -> requests.Response:
    """Make a request to the Lorcast API with rate limiting and timeout."""
    r = session.get(
        query,
        headers={"user-agent": "silhouette-card-maker/0.1", "accept": "*/*"},
        timeout=REQUEST_TIMEOUT,
    )

    # Check for 2XX response code
    r.raise_for_status()

    # Rate limiting
    time.sleep(RATE_LIMIT_SLEEP)

    return r


def get_promo_set_codes() -> list:
    """Return the set codes of the promo-only sets.

    Lorcast's `rarity:` search filter does not recognize "promo" as a value,
    even though "Promo" is a real rarity in the card data. To find promo
    printings, look up sets whose code isn't a normal numbered set (e.g.
    "P1", "cp", "D23") since promo cards are only printed in those sets.

    The result is cached since sets rarely change within a single run.
    """
    global _promo_set_codes_cache

    if _promo_set_codes_cache is None:
        sets_json = request_lorcast(LORCAST_SETS_URL).json()["results"]
        # Normal (non-promo) sets are expected to have a purely numerical set code.
        _promo_set_codes_cache = [
            s["code"] for s in sets_json if not s["code"].isdigit()
        ]

    return _promo_set_codes_cache


def format_lorcast_query(name: str, variant: Optional[str]) -> str:
    """Build a Lorcast search query from a card name and an optional variant.

    Examples:
        format_lorcast_query("Elsa, Spirit of Winter", None)
            -> "Elsa+Spirit+of+Winter"
        format_lorcast_query("Mickey Mouse - True Friend", "enchanted")
            -> "Mickey+Mouse+True+Friend+rarity:enchanted"
        format_lorcast_query("Kuzco - Temperamental Emperor", "promo")
            -> "...+(set:P1+or+set:cp+...)"
        format_lorcast_query("Mickey Mouse - True Friend", "set:P2 cn:15")
            -> "Mickey+Mouse+True+Friend+set:P2+cn:15"
    """
    query = re.sub(r"[^\w]", "+", name)

    if variant == "promo":
        promo_set_codes = get_promo_set_codes()
        if not promo_set_codes:
            raise ValueError("No promo set codes found from Lorcast API")
        set_clause = "+or+".join(f"set:{code}" for code in promo_set_codes)
        query += f"+({set_clause})"
    elif variant and variant.startswith("set:"):
        # A specific print marker (e.g. "set:P2 cn:15") built by
        # deck_formats.py to select an exact printing - append it as-is.
        query += "+" + variant.replace(" ", "+")
    elif variant:
        query += f"+rarity:{variant}"

    return query


def fetch_card(
    index: int,
    quantity: int,
    name: str,
    variant: Optional[str],
    front_img_dir: str,
) -> None:
    """Fetch a card image from the Lorcast API and save it to front_img_dir.

    Args:
        index: Card index in the deck
        quantity: Number of copies to fetch
        name: Card name (may include title after a separator)
        variant: Card rarity variant (e.g. "enchanted") or a specific print
            marker (e.g. "set:P2 cn:15")
        front_img_dir: Directory to save card images

    Raises:
        ValueError: If no card is found or the API response is invalid
        requests.HTTPError: If an API request fails
    """
    # Filter out symbols from card names
    clean_card_name = remove_nonalphanumeric(name)

    # Build query URL
    card_query = format_lorcast_query(name, variant)
    card_info_query = f"{LORCAST_API_URL}?q={card_query}"

    # Query for card info
    response = request_lorcast(card_info_query)
    data = response.json()

    # Validate API response format and that we got results
    if not isinstance(data, dict) or "results" not in data:
        raise ValueError(f"Unexpected API response format: {data}")
    if not data["results"]:
        raise ValueError(f'No cards found for query: "{card_query}"')
    card_json = data["results"][0]

    image_uris = card_json["image_uris"]["digital"]

    # Build the list of candidate image URLs, best quality first. The Lorcast
    # API only exposes small/normal/large AVIF images. The full-size digital
    # image is not listed in the API response today; the `full` key is
    # supported in case the API ever exposes it. Otherwise compute the URL
    # manually: the full image exists on their CDN as the same path with
    # `full` as size and a `.jpg` extension, tried before falling back to
    # the API-provided sizes.
    fallback_image_url = next(
        (
            image_uris[size]
            for size in ("large", "normal", "small")
            if size in image_uris
        ),
        None,
    )
    if "full" in image_uris:
        full_image_url = image_uris["full"]
    else:
        if fallback_image_url is None:
            raise Exception(f'No images available for "{name}"')
        match = re.match(
            r"(.+/digital/)(?:large|normal|small)/(.+)\.avif(\?.*)?$",
            fallback_image_url,
        )
        if match is None:
            raise Exception(
                f'Unexpected image URL format for "{name}": {fallback_image_url}'
            )
        full_image_url = (
            f'{match.group(1)}full/{match.group(2)}.jpg{match.group(3) or ""}'
        )
    image_urls = [url for url in (full_image_url, fallback_image_url) if url]

    card_art = None
    last_error: Optional[Exception] = None
    for image_url in image_urls:
        try:
            logger.debug(f"Fetching card image from: {image_url}")
            content = request_lorcast(image_url).content
        except Exception as error:
            last_error = error
            continue
        # Validate the response decodes as an image now so a corrupt or
        # non-image response triggers the fallback, not later at render time.
        try:
            Image.open(BytesIO(content)).load()
        except Exception as error:
            last_error = error
            continue
        card_art = content
        break

    if card_art is None:
        raise Exception(f'Could not download images for "{name}"') from last_error

    # Save the raw bytes to keep the original file format
    extension = guess_extension(card_art)
    for counter in range(quantity):
        image_path = os.path.join(
            front_img_dir, f"{str(index)}{clean_card_name}{str(counter + 1)}{extension}"
        )
        with open(image_path, "wb") as f:
            f.write(card_art)
        logger.debug(f"Saved card image to: {image_path}")


def get_handle_card(front_img_dir: str):
    """Create a configured fetch_card function for the given directory.

    Args:
        front_img_dir: Directory to save card images

    Returns:
        A configured fetch_card function
    """

    def configured_fetch_card(
        index: int,
        name: str,
        variant: Optional[str],
        quantity: int = 1,
    ):
        fetch_card(
            index,
            quantity,
            name,
            variant,
            front_img_dir,
        )

    return configured_fetch_card
