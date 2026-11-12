import os
import sys

import click

# Add parent directory to path to allow imports when run as a script
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, REPO_ROOT)

from plugins.mtg.common import ScryfallLanguage
from plugins.mtg.deck_formats import DeckFormat, parse_deck, extract_mpcfill_card_ids
from plugins.mtg.scryfall import get_handle_card as scryfall_get_handle_card
from plugins.mtg.mpcfill import get_handle_card as mpc_get_handle_card, prefetch_mpcfill
from utilities import configure_console_encoding, ensure_directory

front_directory = os.path.join(REPO_ROOT, 'game', 'front')
double_sided_directory = os.path.join(REPO_ROOT, 'game', 'double_sided')

@click.command()
@click.argument('deck_path')
@click.argument('format', type=click.Choice([t.value for t in DeckFormat], case_sensitive=False))
@click.option('-i', '--ignore_set_and_collector_number', default=False, is_flag=True, show_default=True, help="Ignore provided sets and collector numbers when fetching cards.")
@click.option('--prefer_older_sets', default=False, is_flag=True, show_default=True, help="Prefer fetching cards from older sets if sets are not provided.")
@click.option('-s', '--prefer_set', multiple=True, help="Prefer fetching cards from a particular set(s) if sets are not provided. Use this option multiple times to specify multiple preferred sets.")
@click.option('--ignore_set', multiple=True, help="Exclude a set from consideration when fetching cards. Use this option multiple times to exclude multiple sets.")
@click.option('--prefer_showcase', default=False, is_flag=True, show_default=True, help="Prefer fetching cards with showcase treatment")
@click.option('--prefer_extra_art', default=False, is_flag=True, show_default=True, help="Prefer fetching cards with full art, borderless, or extended art.")
@click.option('--prefer_lang', multiple=True, type=click.Choice([lang.value for lang in ScryfallLanguage], case_sensitive=False), help="Preferred language for card images (printed code). Use multiple times for a priority list. Falls back to English if none are available.")
@click.option('--prefer_ub', default=False, is_flag=True, show_default=True, help="Prefer Universe Beyond printings when available.")
@click.option('--ignore_ub', default=False, is_flag=True, show_default=True, help="Exclude Universe Beyond printings from consideration.")
@click.option('--tokens', default=False, is_flag=True, show_default=True, help="Fetch related tokens when fetching cards")
@click.option('--exclude_basics', default=False, is_flag=True, show_default=True, help="Skip basic lands (including Wastes and Snow-Covered basics).")

def cli(
    deck_path: str,
    format: DeckFormat,
    ignore_set_and_collector_number: bool,

    prefer_older_sets: bool,
    prefer_set: tuple,
    ignore_set: tuple,

    prefer_showcase: bool,
    prefer_extra_art: bool,

    prefer_lang: tuple,
    prefer_ub: bool,
    ignore_ub: bool,

    tokens: bool,
    exclude_basics: bool,
):
    ensure_directory(front_directory)
    ensure_directory(double_sided_directory)
    if format == DeckFormat.URL:
        deck_text = deck_path
    else:
        if not os.path.isfile(deck_path):
            print(f'{deck_path} is not a valid file.')
            return

        with open(deck_path, 'r') as deck_file:
            deck_text = deck_file.read()

    if format == DeckFormat.MPCFILL_XML:
        get_handle_card = mpc_get_handle_card(
            front_directory,
            double_sided_directory
        )
        prefetch_mpcfill(extract_mpcfill_card_ids(deck_text))
    else:
        get_handle_card = scryfall_get_handle_card(
            ignore_set_and_collector_number,

            prefer_older_sets,
            prefer_set,
            list(ignore_set),

            prefer_showcase,
            prefer_extra_art,
            prefer_ub,
            ignore_ub,

            [ScryfallLanguage(lang) for lang in prefer_lang] or None,

            tokens,

            front_directory,
            double_sided_directory,
        )

    parse_deck(
        deck_text,
        format,
        get_handle_card,
        front_directory,
        double_sided_directory,
        exclude_basics,
    )

if __name__ == '__main__':
    configure_console_encoding()
    cli()
