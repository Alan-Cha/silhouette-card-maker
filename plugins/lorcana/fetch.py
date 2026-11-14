import os
import sys

import click

# Add parent directory to path to allow imports when run as a script
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO_ROOT)

from plugins.lorcana.common import DreambornLanguage, Source
from plugins.lorcana.deck_formats import DeckFormat, parse_deck
from plugins.lorcana.lorcast import get_handle_card as lorcast_get_handle_card
from plugins.lorcana.dreamborn import get_handle_card as dreamborn_get_handle_card
from utilities import configure_console_encoding, ensure_directory

front_directory = os.path.join(REPO_ROOT, "game", "front")


@click.command()
@click.argument("deck_path")
@click.argument(
    "format", type=click.Choice([t.value for t in DeckFormat], case_sensitive=False)
)
@click.option(
    "--source",
    type=click.Choice([t.value for t in Source], case_sensitive=False),
    help='Source of the deck list (default: "dreamborn" if --lang is specified, otherwise "lorcast")',
)
@click.option(
    "--lang",
    type=click.Choice([lang.value for lang in DreambornLanguage], case_sensitive=False),
    default="en",
    help='Language code for card images (default: "en")',
)
def cli(
    deck_path: str,
    format: DeckFormat,
    source: Source,
    lang: str,
):
    ensure_directory(front_directory)
    if not os.path.isfile(deck_path):
        print(f"{deck_path} is not a valid file.")
        return

    with open(deck_path, "r") as deck_file:
        deck_text = deck_file.read()

    if source == Source.DREAMBORN.value or lang is not None:
        get_handle_card = dreamborn_get_handle_card(front_directory, lang)
    else:
        get_handle_card = lorcast_get_handle_card(front_directory)

    parse_deck(deck_text, format, get_handle_card)


if __name__ == "__main__":
    configure_console_encoding()
    cli()
