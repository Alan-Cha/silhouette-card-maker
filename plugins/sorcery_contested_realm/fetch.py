import sys
from os import path
from click import command, argument, option, Choice, Path

# Add parent directory to path to allow imports when run as a script
REPO_ROOT = path.abspath(path.join(path.dirname(__file__), '..', '..'))
sys.path.insert(0, REPO_ROOT)

from plugins.sorcery_contested_realm.deck_formats import DeckFormat, parse_deck
from plugins.sorcery_contested_realm.curiosa import get_handle_card
from utilities import configure_console_encoding, ensure_directory

front_directory = path.join(REPO_ROOT, 'game', 'front')
double_sided_directory = path.join(REPO_ROOT, 'game', 'double_sided')

@command()
@argument('deck_path')
@argument('format', type=Choice([t.value for t in DeckFormat], case_sensitive=False))
@option('--atlas_back', type=Path(exists=True, dir_okay=False), help='The path to an atlas card back image. Sites get this back in game/double_sided/. Put the spellbook card back in game/back/.')

def cli(deck_path: str, format: DeckFormat, atlas_back: str | None):
    ensure_directory(front_directory)
    if atlas_back is not None:
        ensure_directory(double_sided_directory)
    if format != DeckFormat.CURIOSA_URL and not path.isfile(deck_path):
        print(f'{deck_path} is not a valid file.')
        return

    parse_deck(deck_path, format, get_handle_card(front_directory, double_sided_directory, atlas_back))

if __name__ == '__main__':
    configure_console_encoding()
    cli()
