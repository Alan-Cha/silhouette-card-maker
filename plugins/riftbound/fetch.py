from os import path
from click import command, argument, Choice

from deck_formats import DeckFormat, parse_deck
from piltover import fetch_card_art

front_directory = path.join('game', 'front')
double_sided_directory = path.join('game', 'double_sided')

@command()
@argument('deck_path')
@argument('format', type=Choice([t.value for t in DeckFormat], case_sensitive=False))

def cli(deck_path: str, format: DeckFormat):
    if format == DeckFormat.PILTOVER and not path.isfile(deck_path):
        print(f'{deck_path} is not a valid file.')
        return

    with open(deck_path, 'r') as deck_file:
        deck_text = deck_file.read()

        deck = parse_deck(deck_text, format)

        for card_number, quantity in deck.items():
            fetch_card_art(card_number, quantity, front_directory)

if __name__ == '__main__':
    cli()