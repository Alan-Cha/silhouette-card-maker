"""
Tests for the Middle-earth CCG plugin.
Tests deck format parsing, card name resolution and image fetching from the
Council of Elrond cards database.
"""
import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from plugins.middle_earth_ccg import council_of_elrond
from plugins.middle_earth_ccg.council_of_elrond import fetch_card_database, find_card, get_handle_card, normalize_name
from plugins.middle_earth_ccg.deck_formats import DeckFormat, parse_deck


def make_card(card_id, name, alignment, image):
    return {
        "id": card_id,
        "set": card_id.split("-")[0],
        "name": {"en": name, "es": name},
        "type": "Character",
        "alignment": alignment,
        "image": image,
        "rarity": "R1",
    }


def make_set(set_id, *cards):
    base = f"https://cdn.jsdelivr.net/gh/council-of-rivendell/meccg-remaster/en-remaster/{set_id.lower()}/"
    original = f"https://cdn.jsdelivr.net/gh/council-of-rivendell/meccg-remaster/en-original/{set_id.lower()}/"
    return {
        "id": set_id,
        "imageBaseUrl": {"en": base, "enOriginal": original},
        "cards": {card["id"]: card for card in cards},
    }


# Real-shaped excerpt of cards.json (keys are alphabetical, like the real file).
DATABASE = {
    "AS": make_set("AS", make_card("AS-134", "Thrór’s Map", "Minion", "ThrorsMap.jpg"),
                   make_card("AS-160", "Rivendell", "Minion", "Rivendell.jpg")),
    "LE": make_set("LE", make_card("LE-66", "Cave-drake", "Neutral", "Cavedrake.jpg")),
    "TD": make_set("TD", make_card("TD-158", "Thrór’s Map", "Hero", "ThrorsMap.jpg")),
    "TW": make_set("TW", make_card("TW-20", "Cave-drake", "Neutral", "Cavedrake.jpg"),
                   make_card("TW-156", "Gandalf", "Hero", "Gandalf.jpg"),
                   make_card("TW-207", "Dark Quarrels", "Hero", "DarkQuarrels.jpg"),
                   make_card("TW-208", "Dark Quarrels", "Hero", "DarkQuarrels2.jpg"),
                   make_card("TW-421", "Rivendell", "Hero", "Rivendell.jpg")),
    "WH": make_set("WH", make_card("WH-4", "Gandalf", "Fallen-wizard", "Gandalf.jpg")),
}

# Excerpt of a GCCG deck file (as used by play.meccg.com).
GCCG_DECK = """#
# GCCG v0.9.4 Middle-earth deck
#
# A - Stewards of Gondor
#

####
Deck
####

# Hazard (30)

3 Hobgoblins (LE)
1 William - Wûluag (TW)

# Character (8)

3 Saruman [H] (TW)

####
Sites
####

# Sites (15)

1 rivendell [h] (tw)

####
Notes
####

= Starting Companies (2) at Rivendell
1 Glorfindel II (TW) starts with Anborn.
"""

# Excerpt of a Cardnum export.
CARDNUM_DECK = """Pool
1 Adrazar (TW)
1 Théoden (TW)

Resources
2 Dark Quarrels (TW)
2x Cave-drake
"""


def collect(deck_text):
    seen = []
    parse_deck(deck_text, DeckFormat.CARDNUM, lambda index, name, set_code, alignment, quantity: seen.append((name, set_code, alignment, quantity)))
    return seen


# --- Unit Tests ---

class TestDeckFormatEnum:
    def test_cardnum_format_value(self):
        assert DeckFormat.CARDNUM.value == 'cardnum'

    def test_unrecognized_format_raises(self):
        with pytest.raises(ValueError):
            parse_deck("", "not_a_real_format", lambda *args: None)


class TestParseCardnum:
    def test_gccg_deck(self):
        assert collect(GCCG_DECK) == [
            ("Hobgoblins", "LE", "", 3),
            ("William - Wûluag", "TW", "", 1),
            ("Saruman", "TW", "H", 3),
            ("rivendell", "TW", "h", 1),
        ]

    def test_notes_section_is_ignored(self):
        assert "Glorfindel II" not in [name for name, *_ in collect(GCCG_DECK)]

    def test_cardnum_deck_with_optional_set_and_x_quantity(self):
        assert collect(CARDNUM_DECK) == [
            ("Adrazar", "TW", "", 1),
            ("Théoden", "TW", "", 1),
            ("Dark Quarrels", "TW", "", 2),
            ("Cave-drake", "", "", 2),
        ]

    def test_bom_and_crlf(self):
        assert collect("﻿Pool\r\n1 Adrazar (TW)\r\n") == [("Adrazar", "TW", "", 1)]

    def test_errors_from_handle_card_are_collected_not_raised(self, capsys):
        def failing_handle_card(index, name, set_code, alignment, quantity):
            raise ValueError("boom")

        parse_deck(CARDNUM_DECK, DeckFormat.CARDNUM, failing_handle_card)
        assert "Errors:" in capsys.readouterr().out


class TestFindCard:
    def test_normalize_name(self):
        assert normalize_name("Thrór’s Map") == normalize_name("thror's map") == "throrsmap"

    def test_set_and_alignment_disambiguate(self):
        assert find_card(DATABASE, "rivendell", "TW", "h")[1]["id"] == "TW-421"
        assert find_card(DATABASE, "Rivendell", "", "M")[1]["id"] == "AS-160"
        assert find_card(DATABASE, "Thror's Map", "TD", "")[1]["id"] == "TD-158"

    def test_regular_print_preferred_over_promo(self):
        assert find_card(DATABASE, "Dark Quarrels", "TW", "")[1]["id"] == "TW-207"

    def test_earliest_set_preferred_for_reprints(self):
        assert find_card(DATABASE, "Cave-drake", "", "")[1]["id"] == "TW-20"

    def test_different_alignments_are_ambiguous(self):
        with pytest.raises(ValueError, match="TW-156 \\(Hero\\), WH-4 \\(Fallen-wizard\\)"):
            find_card(DATABASE, "Gandalf", "", "")

    def test_unknown_card_raises(self):
        with pytest.raises(ValueError, match="No card found"):
            find_card(DATABASE, "Gandalf", "LE", "")


class TestFetchCardArt:
    def run_fetch(self, tmp_path, content_type, remaster=False):
        response = MagicMock(content=b"\xff\xd8\xff\xe0fakejpeg", headers={"content-type": content_type})
        with patch.object(council_of_elrond, "fetch_card_database", return_value=DATABASE), \
             patch.object(council_of_elrond, "request_council_of_elrond", return_value=response) as mock_request:
            get_handle_card(str(tmp_path), remaster)(4, "Thrór's Map", "TD", "", 2)
        return mock_request

    def test_original_art_saved_once_per_copy(self, tmp_path):
        mock_request = self.run_fetch(tmp_path, "image/jpeg")
        mock_request.assert_called_once_with("https://cdn.jsdelivr.net/gh/council-of-rivendell/meccg-remaster/en-original/td/ThrorsMap.jpg")
        assert sorted(os.listdir(tmp_path)) == ["4ThrórsMap1.jpg", "4ThrórsMap2.jpg"]

    def test_remaster_flag(self, tmp_path):
        mock_request = self.run_fetch(tmp_path, "image/jpeg", remaster=True)
        mock_request.assert_called_once_with("https://cdn.jsdelivr.net/gh/council-of-rivendell/meccg-remaster/en-remaster/td/ThrorsMap.jpg")

    def test_non_image_response_raises(self, tmp_path):
        with pytest.raises(ValueError, match="Expected an image"):
            self.run_fetch(tmp_path, "text/html")
        assert os.listdir(tmp_path) == []


# --- Integration Tests ---

@pytest.mark.integration
class TestCouncilOfElrondDatabase:
    def test_database_has_all_sets(self):
        database = fetch_card_database()
        assert set(database) >= {"TW", "TD", "DM", "LE", "AS", "WH", "BA"}
        assert find_card(database, "Gandalf", "TW", "H")[1]["id"] == "TW-156"


@pytest.mark.integration
class TestFullFetchWorkflow:
    @pytest.fixture
    def front_dir(self):
        front_dir = tempfile.mkdtemp()
        yield front_dir
        shutil.rmtree(front_dir)

    def test_fetch_original_and_remaster(self, front_dir):
        parse_deck("2 Gandalf [H] (TW)\n", DeckFormat.CARDNUM, get_handle_card(front_dir, False))
        parse_deck("1 Cave-drake\n", DeckFormat.CARDNUM, get_handle_card(front_dir, True))

        files = sorted(os.listdir(front_dir))
        assert files == ["1Cavedrake1.jpg", "1Gandalf1.jpg", "1Gandalf2.jpg"]

        for f in files:
            with Image.open(os.path.join(front_dir, f)) as img:
                assert img.height > img.width
