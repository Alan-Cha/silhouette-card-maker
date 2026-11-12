import sys
from os import path
from click import command, argument, option, Choice

# Add parent directory to path to allow imports when run as a script
REPO_ROOT = path.abspath(path.join(path.dirname(__file__), '..', '..'))
sys.path.insert(0, REPO_ROOT)

from plugins.universus.deck_formats import DeckFormat, parse_deck
from plugins.universus.universus import get_handle_card
from utilities import configure_console_encoding, ensure_directory

front_directory = path.join(REPO_ROOT, 'game', 'front')
double_sided_directory = path.join(REPO_ROOT, 'game', 'double_sided')

@command()
@argument('deck_path')
@argument('format', type=Choice([t.value for t in DeckFormat], case_sensitive=False))
@option('--ignore_sideboard', default=False, is_flag=True, show_default=True, help="Skip sideboard cards when fetching cards.")

def cli(deck_path: str, format: DeckFormat, ignore_sideboard: bool):
    ensure_directory(front_directory)
    ensure_directory(double_sided_directory)
    if format != DeckFormat.UNIVERSUS_URL and not path.isfile(deck_path):
        print(f'{deck_path} is not a valid file.')
        return

    parse_deck(deck_path, format, get_handle_card(front_directory, double_sided_directory), ignore_sideboard)

if __name__ == '__main__':
    configure_console_encoding()
    cli()
