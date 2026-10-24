import os
import sys

import click

# Add parent directory to path to allow imports when run as a script
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, REPO_ROOT)

from plugins.warhammer_40k_conquest.deck_formats import DeckFormat, parse_deck
from plugins.warhammer_40k_conquest.conquestdb import get_handle_card
from utilities import configure_console_encoding, ensure_directory

front_directory = os.path.join(REPO_ROOT, 'game', 'front')
double_sided_directory = os.path.join(REPO_ROOT, 'game', 'double_sided')

@click.command()
@click.argument('deck_path')
@click.argument('format', type=click.Choice([t.value for t in DeckFormat], case_sensitive=False))

def cli(deck_path: str, format: DeckFormat):
    ensure_directory(front_directory)
    ensure_directory(double_sided_directory)

    if format == DeckFormat.CONQUESTDB_URL:
        deck_text = deck_path
    else:
        if not os.path.isfile(deck_path):
            print(f'{deck_path} is not a valid file.')
            return

        with open(deck_path, 'r', encoding='utf-8-sig') as deck_file:
            deck_text = deck_file.read()

    parse_deck(
        deck_text,
        format,
        get_handle_card(
            front_directory,
            double_sided_directory,
        ),
    )

if __name__ == '__main__':
    configure_console_encoding()
    cli()
