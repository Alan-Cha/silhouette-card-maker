import os

import click
from deck_formats import DeckFormat, parse_deck
from lorcast import get_handle_card

from typing import Set

front_directory = os.path.join('game', 'front')
double_sided_directory = os.path.join('game', 'double_sided')

@click.command()
@click.argument('deck_path')
@click.argument('format', type=click.Choice([t.value for t in DeckFormat], case_sensitive=False))
#@click.option('-i', '--ignore_set_and_collector_number', default=False, is_flag=True, show_default=True, help="Ignore provided sets and collector numbers when fetching cards.")
#@click.option('--prefer_older_sets', default=False, is_flag=True, show_default=True, help="Prefer fetching cards from older sets if sets are not provided.")
#@click.option('-s', '--prefer_set', multiple=True, help="Prefer fetching cards from a particular set(s) if sets are not provided. Use this option multiple times to specify multiple preferred sets.")
#@click.option('--prefer_showcase', default=False, is_flag=True, show_default=True, help="Prefer fetching cards with showcase treatment")
#@click.option('--prefer_extra_art', default=False, is_flag=True, show_default=True, help="Prefer fetching cards with full art, borderless, or extended art.")

def cli(
    deck_path: str,
    format: DeckFormat,
    #ignore_set_and_collector_number: bool,
    #prefer_older_sets: bool,
    #prefer_set: Set[str],

    #prefer_showcase: bool,
    #prefer_extra_art: bool
):
    if not os.path.isfile(deck_path):
        print(f'{deck_path} is not a valid file.')
        return

    with open(deck_path, 'r') as deck_file:
        deck_text = deck_file.read()

        parse_deck(
            deck_text,
            format,
            get_handle_card(
                #ignore_set_and_collector_number,

                #prefer_older_sets,
                #prefer_set,
                
                #prefer_showcase,
                #prefer_extra_art,

                front_directory,
                double_sided_directory
            )
        )

if __name__ == '__main__':
    cli()