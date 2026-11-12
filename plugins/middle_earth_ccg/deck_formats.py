from enum import Enum
from re import compile
from typing import Callable, List, Tuple

card_data_tuple = Tuple[str, str, str, int] # name, set code, alignment, quantity

def parse_deck_helper(
        deck_text: str,
        handle_card: Callable,
        deck_splitter: Callable[[str], List[str]],
        is_card_line: Callable[[str], bool],
        extract_card_data: Callable[[str], card_data_tuple],
    ) -> None:
    error_lines = []

    index = 0

    for line in deck_splitter(deck_text):
        if is_card_line(line):
            index = index + 1

            name, set_code, alignment, quantity = extract_card_data(line)

            parts = [f'Index: {index}', f'quantity: {quantity}', f'name: {name}']
            if alignment: parts.append(f'alignment: {alignment}')
            if set_code: parts.append(f'set: {set_code}')
            print(', '.join(parts))
            try:
                handle_card(index, name, set_code, alignment, quantity)
            except Exception as e:
                print(f'Error: {e}')
                error_lines.append((line, e))
        else:
            print(f'Skipping: "{line}"')

    if len(error_lines) > 0:
        print(f'Errors: {error_lines}')

# Cardnum / GCCG / play.meccg.com format. Section headers ("Pool", "Resources",
# "# Hazard (30)", "####") are skipped and every section is fetched, including
# the sideboard and sites. GCCG's free-text "Notes" section is ignored.
#   Pool
#   1 Glorfindel II (TW)
#   3 Saruman [H] (TW)
#   1 rivendell [h] (tw)
#   2x Cave-drake
def parse_cardnum(deck_text: str, handle_card: Callable):
    # '{quantity}[x] {name} [{alignment}] ({set code})', alignment and set code optional
    pattern = compile(r'^(\d+)x?\s+(.+?)(?:\s+\[(\w+)\])?(?:\s+\((\w+)\))?$')

    def is_cardnum_line(line) -> bool:
        return bool(pattern.match(line))

    def extract_cardnum_card_data(line) -> card_data_tuple:
        match = pattern.match(line)
        quantity = int(match.group(1))
        name = match.group(2).strip()
        alignment = match.group(3) or ''
        set_code = (match.group(4) or '').upper()

        return (name, set_code, alignment, quantity)

    def split_cardnum_deck(deck_text: str) -> List[str]:
        lines = []
        for line in deck_text.strip().splitlines():
            line = line.strip()
            if line.lower() == 'notes':
                break
            if line:
                lines.append(line)
        return lines

    parse_deck_helper(deck_text, handle_card, split_cardnum_deck, is_cardnum_line, extract_cardnum_card_data)

class DeckFormat(str, Enum):
    CARDNUM = 'cardnum'

def parse_deck(deck_text: str, format: DeckFormat, handle_card: Callable):
    if format == DeckFormat.CARDNUM:
        parse_cardnum(deck_text, handle_card)
    else:
        raise ValueError('Unrecognized deck format.')
