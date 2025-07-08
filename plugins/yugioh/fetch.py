# TO DO
# Add YDKe support from file (take line arg?)
# Ensure no other formats exist
# Progress display?
# Retrofit Lorcana with more generic naming conventions
 


import os

import click
from deck_formats import DeckFormat, parse_deck
from api import fetch_card_art

from typing import Set

front_directory = os.path.join('game', 'front')
double_sided_directory = os.path.join('game', 'double_sided')

@click.command()
@click.argument('deck_path')
@click.argument('format', type=click.Choice([t.value for t in DeckFormat], case_sensitive=False))

def cli(deck_path: str, format: DeckFormat):
    if format==DeckFormat.YDK and not os.path.isfile(deck_path):
        print(f'{deck_path} is not a valid file.')
        return

    cards = parse_deck(deck_path,format)

    for passcode, quantity in cards.items():
        fetch_card_art(passcode,quantity,front_directory)

    print('Task complete.')

if __name__ == '__main__':
    cli()