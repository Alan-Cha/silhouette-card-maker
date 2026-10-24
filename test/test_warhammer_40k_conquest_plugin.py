"""
Tests for the Warhammer 40,000: Conquest plugin.
Tests deck format parsing and image fetching from ConquestDB.
"""
import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from plugins.warhammer_40k_conquest import conquestdb
from plugins.warhammer_40k_conquest.conquestdb import card_image_name, fetch_deck_text, get_handle_card
from plugins.warhammer_40k_conquest.deck_formats import DECK_URL_PATTERN, DeckFormat, parse_deck


# Shape of the "Download Deck" text from https://www.conquestdb.com/decks/Echo/Zq99g5gmBTdfq8cg/
CONQUESTDB_DECK = """Square root of 7 kyubed
----------------------------------------------------------------------
Grigory Maksim
Astra Militarum
----------------------------------------------------------------------
Signature Squad

4x Maksim's Squadron
1x Clearing the Path
2x Keep Firing!
1x Searchlight
----------------------------------------------------------------------
Army

3x Krieg Armoured Regiment
----------------------------------------------------------------------
Synapse


----------------------------------------------------------------------
Planet

"""

DECK_PAGE_HTML = """<script>
    var deck_text = "Deck|||----------|||Grigory Maksim|||Astra Militarum|||----------|||Signature Squad||||||4x Maksim&#x27;s Squadron|||----------|||Event||||||2x Keep Firing!";
    deck_text = deck_text.split("|||").join("\\n");
</script>"""


def collect(seen):
    return lambda index, name, quantity, warlord: seen.append((index, name, quantity, warlord))


# --- Unit Tests ---

class TestDeckFormatEnum:
    """Test the DeckFormat enum values."""

    def test_format_values(self):
        assert DeckFormat.CONQUESTDB.value == 'conquestdb'
        assert DeckFormat.CONQUESTDB_URL.value == 'conquestdb_url'


class TestParseConquestdb:
    """Test the conquestdb text format."""

    def test_parses_warlord_and_cards(self):
        seen = []
        parse_deck(CONQUESTDB_DECK, DeckFormat.CONQUESTDB, collect(seen))

        assert seen == [
            (1, "Grigory Maksim", 1, True),
            (2, "Maksim's Squadron", 4, False),
            (3, "Clearing the Path", 1, False),
            (4, "Keep Firing!", 2, False),
            (5, "Searchlight", 1, False),
            (6, "Krieg Armoured Regiment", 3, False),
        ]

    def test_plain_list_has_no_warlord(self):
        seen = []
        parse_deck("4x Maksim's Squadron\r\n2x Keep Firing!\r\n", DeckFormat.CONQUESTDB, collect(seen))

        assert seen == [(1, "Maksim's Squadron", 4, False), (2, "Keep Firing!", 2, False)]

    def test_section_header_after_separator_is_not_a_warlord(self):
        seen = []
        parse_deck("4x Searchlight\n-----\nArmy\n1x Holy Battery", DeckFormat.CONQUESTDB, collect(seen))

        assert seen == [(1, "Searchlight", 4, False), (2, "Holy Battery", 1, False)]

    def test_errors_from_handle_card_are_collected_not_raised(self):
        def failing_handle_card(index, name, quantity, warlord):
            raise ValueError("boom")

        parse_deck(CONQUESTDB_DECK, DeckFormat.CONQUESTDB, failing_handle_card)

    def test_unrecognized_format_raises(self):
        with pytest.raises(ValueError):
            parse_deck("", "not_a_real_format", lambda *args: None)


class TestParseConquestdbUrl:
    """Test the conquestdb_url format with the deck page request mocked."""

    def test_url_pattern(self):
        match = DECK_URL_PATTERN.match("https://www.conquestdb.com/decks/Echo/Zq99g5gmBTdfq8cg/")
        assert match.groups() == ("Echo", "Zq99g5gmBTdfq8cg")
        assert DECK_URL_PATTERN.match("https://conquestdb.com/decks/Echo/Zq99g5gmBTdfq8cg")
        assert not DECK_URL_PATTERN.match("https://www.conquestdb.com/cards/Grigory_Maksim/")
        assert not DECK_URL_PATTERN.match("https://example.com/decks/Echo/Zq99g5gmBTdfq8cg/")

    def test_parses_embedded_deck_text(self):
        response = MagicMock(text=DECK_PAGE_HTML)

        seen = []
        with patch.object(conquestdb, "request_conquestdb", return_value=response) as mock_request:
            parse_deck("https://www.conquestdb.com/decks/Echo/Zq99g5gmBTdfq8cg/", DeckFormat.CONQUESTDB_URL, collect(seen))

        mock_request.assert_called_once_with("https://www.conquestdb.com/decks/Echo/Zq99g5gmBTdfq8cg/")
        assert seen == [
            (1, "Grigory Maksim", 1, True),
            (2, "Maksim's Squadron", 4, False),
            (3, "Keep Firing!", 2, False),
        ]

    def test_page_without_deck_text_raises(self):
        with patch.object(conquestdb, "request_conquestdb", return_value=MagicMock(text="<html></html>")):
            with pytest.raises(ValueError):
                fetch_deck_text("Echo", "missing")


class TestCardImageName:
    """Test the card name to ConquestDB image filename conversion."""

    @pytest.mark.parametrize("name,image_name", [
        ("Catachan Outpost", "Catachan_Outpost"),
        ("Maksim's Squadron", "Maksim's_Squadron"),
        ("Vitarus, the Sanguine Sword", "Vitarus,_the_Sanguine_Sword"),
        ("\"Subject: Ω-X62113\"", "Subject_Ω-X62113"),
        ("Ulthwé Spirit Stone", "Ulthwé_Spirit_Stone"),
    ])
    def test_card_image_name(self, name, image_name):
        assert card_image_name(name) == image_name


class TestFetchCardArt:
    """Test image saving with requests mocked."""

    def test_rejects_non_image_response(self, tmp_path):
        response = MagicMock(headers={"content-type": "text/html"}, content=b"<html>")

        with patch.object(conquestdb, "request_conquestdb", return_value=response):
            with pytest.raises(ValueError):
                conquestdb.fetch_card_art(1, "Not A Card", 1, False, str(tmp_path), str(tmp_path))

        assert list(tmp_path.iterdir()) == []

    def test_warlord_saves_bloodied_back(self, tmp_path):
        front_dir = tmp_path / "front"
        double_sided_dir = tmp_path / "double_sided"
        front_dir.mkdir()
        double_sided_dir.mkdir()

        response = MagicMock(headers={"content-type": "image/jpeg"}, content=b"\xff\xd8\xff\xe0\x00\x10JFIF\x00")

        with patch.object(conquestdb, "request_conquestdb", return_value=response) as mock_request:
            conquestdb.fetch_card_art(1, "Grigory Maksim", 1, True, str(front_dir), str(double_sided_dir))

        assert mock_request.call_args_list[1].args[0].endswith("/Grigory_Maksim_bloodied.jpg")
        assert os.listdir(front_dir) == ["1GrigoryMaksim1.jpg"]
        assert os.listdir(double_sided_dir) == ["1GrigoryMaksim1.jpg"]


# --- Integration Tests ---

@pytest.mark.integration
class TestFullFetchWorkflow:
    """Integration tests for the complete card fetching workflow."""

    @pytest.fixture
    def temp_dirs(self):
        front_dir = tempfile.mkdtemp()
        double_sided_dir = tempfile.mkdtemp()
        yield front_dir, double_sided_dir
        shutil.rmtree(front_dir)
        shutil.rmtree(double_sided_dir)

    def test_fetch_cards_from_conquestdb_text(self, temp_dirs):
        front_dir, double_sided_dir = temp_dirs

        deck_text = "----------\nGrigory Maksim\nAstra Militarum\n----------\n2x Maksim's Squadron"

        parse_deck(deck_text, DeckFormat.CONQUESTDB, get_handle_card(front_dir, double_sided_dir))

        # warlord (1) + Maksim's Squadron (2 copies) = 3 fronts, plus the warlord's bloodied back
        front_files = os.listdir(front_dir)
        assert len(front_files) == 3
        assert os.listdir(double_sided_dir) == ["1GrigoryMaksim1.jpg"]

        for f in front_files:
            with Image.open(os.path.join(front_dir, f)) as img:
                img.verify()

    def test_fetch_deck_text_from_conquestdb_url(self):
        deck_text = fetch_deck_text("Echo", "Zq99g5gmBTdfq8cg")

        seen = []
        parse_deck(deck_text, DeckFormat.CONQUESTDB, collect(seen))

        assert seen[0] == (1, "Grigory Maksim", 1, True)
        assert sum(quantity for _, _, quantity, _ in seen) == 51
