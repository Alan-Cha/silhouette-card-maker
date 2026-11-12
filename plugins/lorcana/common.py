import re
from enum import Enum


def remove_nonalphanumeric(s: str) -> str:
    return re.sub(r"[^\w]", "", s)


# Lorcana cards are normally printed at one of five rarities: Common,
# Uncommon, Rare, Super Rare, and Legendary. Some cards additionally get a
# special alternate-art printing at one of the variant rarities below. See:
# https://lorcast.com/docs/syntax#rarity and https://lorcast.com/docs/api/cards
class CardVariant(str, Enum):
    ENCHANTED = "enchanted"
    EPIC = "epic"
    ICONIC = "iconic"
    PROMO = "promo"


class Source(Enum):
    DREAMBORN = "dreamborn"
    LORCAST = "lorcast"


class DreambornLanguage(Enum):
    ENGLISH = "en"
    FRENCH = "fr"
    DEUTSCHE = "de"
    ITALIAN = "it"
    SPANISH = "es"
    JAPANESE = "ja"
