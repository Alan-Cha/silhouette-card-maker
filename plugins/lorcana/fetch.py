import os

import click
from deck_formats import DeckFormat, parse_deck
from lorcast import get_handle_card

front_directory = os.path.join('game', 'front')

@click.command()
@click.argument('deck_path')
@click.argument('format', type=click.Choice([t.value for t in DeckFormat], case_sensitive=False))

def cli(
    deck_path: str,
    format: DeckFormat,
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
                front_directory
            )
        )

if __name__ == '__main__':
    cli()