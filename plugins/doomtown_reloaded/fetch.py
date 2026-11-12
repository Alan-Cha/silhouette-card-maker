import os
import sys

import click

# Add parent directory to path to allow imports when run as a script
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, REPO_ROOT)

from plugins.doomtown_reloaded.deck_formats import DeckFormat, parse_deck
from plugins.doomtown_reloaded.dtdb import get_handle_card
from utilities import configure_console_encoding, ensure_directory

front_directory = os.path.join(REPO_ROOT, 'game', 'front')
double_sided_directory = os.path.join(REPO_ROOT, 'game', 'double_sided')

@click.command()
@click.argument('deck_path')
@click.argument('format', type=click.Choice([t.value for t in DeckFormat], case_sensitive=False))

def cli(deck_path: str, format: DeckFormat):
    ensure_directory(front_directory)
    ensure_directory(double_sided_directory)

    # A dtdb URL can be passed directly instead of a file containing it.
    if os.path.isfile(deck_path):
        with open(deck_path, 'r', encoding='utf-8-sig') as deck_file:
            deck_text = deck_file.read()
    else:
        deck_text = deck_path

    parse_deck(deck_text, format, get_handle_card(front_directory))

if __name__ == '__main__':
    configure_console_encoding()
    cli()
