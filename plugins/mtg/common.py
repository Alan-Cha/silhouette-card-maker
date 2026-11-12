import re
from enum import Enum

def remove_nonalphanumeric(s: str) -> str:
    return re.sub(r'[^\w]', '', s)

BASIC_LAND_NAMES = {
    'plains', 'island', 'swamp', 'mountain', 'forest', 'wastes',
    'snow-covered plains', 'snow-covered island', 'snow-covered swamp',
    'snow-covered mountain', 'snow-covered forest',
}

def is_basic_land(name: str) -> bool:
    return name.strip().casefold() in BASIC_LAND_NAMES

class ScryfallLanguage(Enum):
    ENGLISH            = "en"
    SPANISH            = "sp"
    FRENCH             = "fr"
    GERMAN             = "de"
    ITALIAN            = "it"
    PORTUGUESE         = "pt"
    JAPANESE           = "jp"
    KOREAN             = "kr"
    RUSSIAN            = "ru"
    SIMPLIFIED_CHINESE = "cs"
    TRADITIONAL_CHINESE = "ct"
    ANCIENT_GREEK      = "ag"
    PHYREXIAN          = "ph"

# Maps the printed code (enum value) to the Scryfall API language code
PRINTED_TO_API_LANG: dict[str, str] = {
    "en": "en",
    "sp": "es",
    "fr": "fr",
    "de": "de",
    "it": "it",
    "pt": "pt",
    "jp": "ja",
    "kr": "ko",
    "ru": "ru",
    "cs": "zhs",
    "ct": "zht",
    "ag": "grc",
    "ph": "ph",
}

def to_scryfall_api_lang(lang: ScryfallLanguage) -> str:
    return PRINTED_TO_API_LANG[lang.value]