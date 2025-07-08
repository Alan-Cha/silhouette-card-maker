# Based on https://github.com/Yeet195/DeckParser

import numpy as np
import base64
from enum import Enum

def cards(deck):
    # Converts decks from [[main][extra][side]] to {[passcode]:[quantity]}
    card_dict = {}
    for subdeck in deck:
        for card in subdeck:
            card_dict[card] = card_dict.get(card, 0) + 1

    return card_dict

def base64_to_passcodes(b64_string):
    return np.frombuffer(base64.b64decode(b64_string), dtype=np.uint32).tolist()

def parse_ydke(file_path):
    if not (file_path.startswith("ydke://") or file_path.endswith(".txt")):
        raise ValueError('Unrecognized YDKe format. Expected valid file path or "ydke://[main]![extra]![side]!"')

    if file_path.endswith(".txt"):
        ydke_text = open(file_path,"r").read()

    else:
        ydke_text = file_path.replace("\"","")

    components = ydke_text[len("ydke://"):].split("!")
    if len(components) != 4:
        raise ValueError('Unrecognized YDKe format. Expected "ydke://[main]![extra]![side]!"')

    return [
        base64_to_passcodes(components[0]),
        base64_to_passcodes(components[1]),
        base64_to_passcodes(components[2])
    ]

def parse_ydk(file_path):
    deck = {"#main": [], "#extra": [], "!side": []}
    current_section = None

    with open(file_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            if line in deck:
                current_section = line
                continue

            if current_section != None and line.isdigit():
                deck[current_section].append(int(line))

    return [
        deck["#main"],
        deck["#extra"],
        deck["!side"]
    ]

class DeckFormat(str, Enum):
    YDKE = "ydke"
    YDK = "ydk"

def parse_deck(file_path: str, format: DeckFormat):
    if format == DeckFormat.YDKE:
        deck = parse_ydke(file_path)
    elif format == DeckFormat.YDK:
        deck = parse_ydk(file_path)
    else:
        raise ValueError("Unrecognized deck format.")

    return cards(deck)