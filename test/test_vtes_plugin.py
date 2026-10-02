"""
Tests for the Vampire: The Eternal Struggle plugin.
Tests deck format parsing and image fetching from KRCG.
"""
import os
import shutil
import tempfile
from unittest.mock import patch

import pytest
from PIL import Image

from plugins.vtes import deck_formats
from plugins.vtes.deck_formats import DeckFormat, extract_text_card_data, parse_deck
from plugins.vtes.krcg import fetch_card_json, get_handle_card


# Shape of a TWDA text deck (also produced by Amaranth and VDB exports).
TWDA_TEXT = """German NC 2016
Bochum, Germany
19 players

Crypt (12 cards, min=8, max=21, avg=3.75)
-----------------------------------------
2x Stick               3  ANI                      Nosferatu antitribu:4
1x Theo Bell (ADV)     7  CEL DOM POT pre          Brujah:2
1x Anarch Convert      1  -none-                   Caitiff:ANY

Library (90 cards)
Master (12)
5x Blood Doll
1x Rack, The

Combat (38)
16x Aid from Bats  -- the core of the deck
"""

# Lackey export: '{quantity}<tab>{name}', crypt after the library.
LACKEY_TEXT = "5\tBlood Doll\n16\tAid from Bats\nCrypt:\n2\tStick\n1\tTheo Bell (ADV)\n"

# Shape of https://api.krcg.org/twda/{id}
TWDA_JSON = {
    "id": "2016gncbg",
    "crypt": {"count": 3, "cards": [
        {"count": 2, "id": 201318, "name": "Stick"},
        {"count": 1, "id": 200673, "name": "Janey Pickman"},
    ]},
    "library": {"count": 21, "cards": [
        {"count": 5, "type": "Master", "cards": [{"count": 5, "id": 100199, "name": "Blood Doll"}]},
        {"count": 16, "type": "Combat", "cards": [{"count": 16, "id": 100029, "name": "Aid from Bats"}]},
    ]},
}


def collect(deck_text, format):
    seen = []
    parse_deck(deck_text, format, lambda index, card_id, quantity: seen.append((card_id, quantity)))
    return seen


# --- Unit Tests ---

class TestDeckFormatEnum:
    def test_format_values(self):
        assert DeckFormat.TEXT.value == 'text'
        assert DeckFormat.TWDA.value == 'twda'

    def test_unrecognized_format_raises(self):
        with pytest.raises(ValueError):
            parse_deck("", "not_a_real_format", lambda *args: None)


class TestTextFormat:
    def test_crypt_line_uses_group_column(self):
        assert extract_text_card_data(
            "2x Stick               3  ANI                      Nosferatu antitribu:4"
        ) == ("Stick", "Stick (G4)", 2)

    def test_advanced_vampire_keeps_adv_with_group(self):
        assert extract_text_card_data(
            "1x Theo Bell (ADV)     7  CEL DOM POT pre          Brujah:2"
        ) == ("Theo Bell (ADV)", "Theo Bell (G2 ADV)", 1)

    def test_any_group_is_looked_up_by_name(self):
        assert extract_text_card_data(
            "1x Anarch Convert      1  -none-                   Caitiff:ANY"
        ) == ("Anarch Convert", "Anarch Convert", 1)

    def test_library_line_strips_comment(self):
        assert extract_text_card_data("16x Aid from Bats  -- the core of the deck") == ("Aid from Bats", "Aid from Bats", 16)

    def test_non_card_lines_are_skipped(self):
        assert extract_text_card_data("19 players") is None
        assert extract_text_card_data("Crypt (12 cards, min=8, max=21, avg=3.75)") is None
        assert extract_text_card_data("Master (12)") is None

    def test_parse_twda_text(self):
        assert collect(TWDA_TEXT, DeckFormat.TEXT) == [
            ("Stick (G4)", 2),
            ("Theo Bell (G2 ADV)", 1),
            ("Anarch Convert", 1),
            ("Blood Doll", 5),
            ("Rack, The", 1),
            ("Aid from Bats", 16),
        ]

    def test_parse_lackey_text(self):
        assert collect(LACKEY_TEXT, DeckFormat.TEXT) == [
            ("Blood Doll", 5),
            ("Aid from Bats", 16),
            ("Stick", 2),
            ("Theo Bell (ADV)", 1),
        ]

    def test_errors_from_handle_card_are_collected_not_raised(self):
        def failing_handle_card(index, card_id, quantity):
            raise ValueError("boom")

        parse_deck(TWDA_TEXT, DeckFormat.TEXT, failing_handle_card)


class TestTwdaFormat:
    @pytest.mark.parametrize("deck_text", [
        "2016gncbg",
        "https://api.krcg.org/twda/2016gncbg",
        "https://vdb.im/decks/2016gncbg/",
    ])
    def test_deck_id_is_extracted_and_cards_use_ids(self, deck_text):
        with patch.object(deck_formats, "fetch_twda_deck", return_value=TWDA_JSON) as mock_fetch:
            seen = collect(deck_text, DeckFormat.TWDA)

        mock_fetch.assert_called_once_with("2016gncbg")
        assert seen == [(201318, 2), (200673, 1), (100199, 5), (100029, 16)]


# --- Integration Tests ---

@pytest.mark.integration
class TestKRCGAPI:
    def test_vampire_group_and_adv_lookup(self):
        card = fetch_card_json("Theo Bell (G2 ADV)")
        assert card.get("id") == 201363
        assert card.get("url")

    def test_twda_style_library_name_lookup(self):
        assert fetch_card_json("Rack, The").get("id") == 101536


@pytest.mark.integration
class TestFullFetchWorkflow:
    @pytest.fixture
    def front_dir(self):
        front_dir = tempfile.mkdtemp()
        yield front_dir
        shutil.rmtree(front_dir)

    def test_fetch_text_deck(self, front_dir):
        parse_deck("2x Stick  3  ANI  Nosferatu antitribu:4\n1x Blood Doll", DeckFormat.TEXT, get_handle_card(front_dir))

        files = sorted(os.listdir(front_dir))
        assert files == ["1StickG41.jpg", "1StickG42.jpg", "2BloodDoll1.jpg"]

        for f in files:
            with Image.open(os.path.join(front_dir, f)) as img:
                assert img.height > img.width
