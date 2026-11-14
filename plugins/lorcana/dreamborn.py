import logging
import os
import re
import requests
import time
from io import BytesIO
from typing import Optional

from PIL import Image

from plugins.lorcana.common import CardVariant, remove_nonalphanumeric
from utilities import guess_extension

logger = logging.getLogger(__name__)

# API Constants
DREAMBORN_API_URL = "https://dreamborn.ink/api/v2/cards"
DREAMBORN_CDN_URL = "https://cdn.dreamborn.ink/images/{lang}/cards/{card_id}"

# Request timeout in seconds
REQUEST_TIMEOUT = 30

# Rate limiting sleep in seconds
RATE_LIMIT_SLEEP = 0.075

# Card name separators
NAME_SEPARATORS = [",", "-", ":"]

session = requests.Session()


def request_dreamborn(query: str) -> requests.Response:
    """Make a request to Dreamborn API with rate limiting and timeout."""
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


def format_dreamborn_name(name: str) -> str:
    """Extract the card name (part before separator) and clean it.

    Handles multiple separator formats: comma, hyphen, colon.

    Examples:
        "Elsa, Spirit of Winter" -> "Elsa"
        "Simba - King of the Pride Lands" -> "Simba"
        "Mickey Mouse: True Friend" -> "MickeyMouse"
        "Mulan" -> "Mulan"
    """
    for separator in NAME_SEPARATORS:
        if separator in name:
            parts = name.split(separator, 1)
            return remove_nonalphanumeric(parts[0].strip())
    return remove_nonalphanumeric(name.strip())


def format_dreamborn_title(name: str) -> str:
    """Extract the card title (part after separator) and clean it.

    Handles multiple separator formats: comma, hyphen, colon.

    Examples:
        "Elsa, Spirit of Winter" -> "SpiritofWinter"
        "Simba - King of the Pride Lands" -> "KingofthePrideLands"
        "Mickey Mouse: True Friend" -> "TrueFriend"
        "Mulan" -> ""
    """
    for separator in NAME_SEPARATORS:
        if separator in name:
            parts = name.split(separator, 1)
            return remove_nonalphanumeric(parts[1].strip())
    return ""


def fetch_card(
    index: int,
    quantity: int,
    name: str,
    variant: Optional[str],
    front_img_dir: str,
    lang: str = "en",
) -> None:
    """Fetch card image from Dreamborn API and save to front_img_dir.

    Args:
        index: Card index in the deck
        quantity: Number of copies to fetch
        name: Card name (may include title after comma)
        variant: Card variant/rarious (e.g., "Enchanted", "Common")
        front_img_dir: Directory to save card images
        lang: Language code for card images (default: "en")

    Raises:
        ValueError: If no card is found or API response is invalid
        requests.HTTPError: If API request fails
    """
    # Filter out symbols from card names
    clean_name = format_dreamborn_name(name)
    clean_title = format_dreamborn_title(name)

    # Build query URL
    card_info_query = f"{DREAMBORN_API_URL}?name={clean_name}&title={clean_title}"

    # Query for card info
    response = request_dreamborn(card_info_query)
    data = response.json()

    # Validate API response format
    if not isinstance(data, (list, dict)):
        raise ValueError(f"Unexpected API response format: {type(data)}")

    # Extract results list
    results = data if isinstance(data, list) else data.get("results", [])

    # Validate we got results
    if not results:
        raise ValueError(
            f'No cards found for query: name="{clean_name}", title="{clean_title}"'
        )

    # If variant is specified, try to find a matching card
    if variant and results:
        variant_lower = variant.lower()
        exact_match = None
        set_fallback = None

        for card in results:
            card_number = card.get("number", "").upper()
            card_rarity = card.get("rarity", "").lower()
            card_id = card.get("id", "")

            # Check for rarity variants (Enchanted, Epic, Iconic, Promo)
            if variant_lower in CardVariant:
                if card_rarity == variant_lower:
                    exact_match = card
                    break
            # Check for print variants (set:P1, set:P2 cn:15)
            elif variant_lower.startswith("set:"):
                # Parse set code and collector number
                match = re.match(r"set:([A-Za-z0-9]+)(?:\s+cn:(\d+))?", variant_lower)
                if match:
                    set_code = match.group(1).upper()
                    collector_number = match.group(2)

                    if collector_number:
                        # Exact match: look for "25/P1" or "025/P1" in number
                        expected_exact = f"{int(collector_number)}/{set_code}"
                        expected_padded = f"{int(collector_number):03d}/{set_code}"
                        if (
                            expected_exact in card_number
                            or expected_padded in card_number
                        ):
                            if exact_match is None:
                                exact_match = card
                    else:
                        # Fallback: any card with /P1 in number
                        if f"/{set_code}" in card_number:
                            if set_fallback is None:
                                set_fallback = card
            # Default: try to match by rarity
            else:
                if card_rarity == variant_lower:
                    exact_match = card
                    break

        # Use exact match first, then fallback to same set, then first result
        card_json = exact_match or set_fallback or results[0]

        logger.debug(
            f'Using {"exact match" if exact_match else "fallback" if set_fallback else "first"} card '
            f'for variant "{variant}"'
        )
    else:
        card_json = results[0]

    if card_json is None:
        raise ValueError(
            f'No matching card found for name="{clean_name}", '
            f'title="{clean_title}", variant="{variant}"'
        )

    card_id = card_json.get("id")
    if not card_id:
        raise ValueError(f'Card found but missing "id" field: {card_json}')

    # Fetch card image with fallback to English if requested language not available
    image_url = DREAMBORN_CDN_URL.format(lang=lang, card_id=card_id)
    logger.debug(f"Fetching card image from: {image_url}")

    # Download and validate the response decodes as an image now, so a
    # corrupt or non-image response raises here, not later at render time.
    def download_card_image(url: str) -> bytes:
        content = request_dreamborn(url).content
        Image.open(BytesIO(content)).load()
        return content

    try:
        card_art = download_card_image(image_url)
    except requests.HTTPError as e:
        if e.response.status_code == 404 and lang != "en":
            card_lang = card_json.get("language", "en")
            logger.warning(
                f"↳ Card image not found for lang='{lang}', "
                f"falling back to lang='{card_lang}'"
            )
            fallback_url = DREAMBORN_CDN_URL.format(lang=card_lang, card_id=card_id)
            logger.debug(f"Fetching fallback card image from: {fallback_url}")
            card_art = download_card_image(fallback_url)
        else:
            raise

    # Save the raw bytes to keep the original file format
    extension = guess_extension(card_art)
    for counter in range(quantity):
        image_path = os.path.join(
            front_img_dir,
            f"{index}{clean_name}{clean_title}{counter + 1}{extension}",
        )
        with open(image_path, "wb") as f:
            f.write(card_art)
        logger.debug(f"Saved card image to: {image_path}")


def get_handle_card(
    front_img_dir: str,
    lang: str = "en",
):
    """Create a configured fetch_card function for the given directory and language.

    Args:
        front_img_dir: Directory to save card images
        lang: Language code for card images (default: "en")

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
            lang,
        )

    return configured_fetch_card
