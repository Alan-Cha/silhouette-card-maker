import sys
from os import path
from click import command, argument, Choice

# Add parent directory to path to allow imports when run as a script
REPO_ROOT = path.abspath(path.join(path.dirname(__file__), '..', '..'))
sys.path.insert(0, REPO_ROOT)

from plugins.pokemon.deck_formats import DeckFormat, parse_deck
from plugins.pokemon.limitless import get_handle_card as get_limitless_handle_card
from plugins.pokemon.pkmtts import get_handle_card as get_pkmtts_handle_card
from utilities import ensure_directory

front_directory = path.join(REPO_ROOT, 'game', 'front')

HANDLE_CARD_GETTERS = {
    DeckFormat.LIMITLESS: get_limitless_handle_card,
    DeckFormat.PKMTTS: get_pkmtts_handle_card,
}

@command()
@argument('deck_path')
@argument('format', type=Choice([t.value for t in DeckFormat], case_sensitive=False))

def cli(deck_path: str, format: DeckFormat):
    ensure_directory(front_directory)
    if not path.isfile(deck_path):
        print(f'{deck_path} is not a valid file.')
        return

    get_handle_card = HANDLE_CARD_GETTERS[format]

    with open(deck_path, 'r') as deck_file:
        deck_text = deck_file.read()

        parse_deck(deck_text, format, get_handle_card(front_directory))

if __name__ == '__main__':
    cli()
