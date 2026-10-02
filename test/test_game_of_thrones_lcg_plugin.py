"""
Tests for the A Game of Thrones: The Card Game (Second Edition) plugin.
Tests deck format parsing and image fetching from ThronesDB.
"""
import json
import os
import shutil
import tempfile
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from plugins.game_of_thrones_lcg import api
from plugins.game_of_thrones_lcg.deck_formats import DeckFormat, DECKLIST_URL_PATTERN, parse_deck, parse_deck_helper
from plugins.game_of_thrones_lcg.api import fetch_card_catalog, fetch_decklist, get_handle_card


def image_bytes(width: int, height: int, format: str = 'JPEG') -> bytes:
    buffer = BytesIO()
    Image.new('RGB', (width, height)).save(buffer, format=format)
    return buffer.getvalue()


def image_response(content: bytes, content_type: str = 'image/jpeg') -> MagicMock:
    response = MagicMock()
    response.content = content
    response.headers = {'content-type': content_type}
    return response


# Shape of a https://thronesdb.com/api/public/decklist/<id> response (trimmed).
DECKLIST_JSON = {
    "id": 1,
    "name": "Secrets and Schemes (1 core set)",
    "faction_code": "lannister",
    "faction_name": "House Lannister",
    "slots": {"01003": 1, "01028": 2, "01205": 1},
    "agendas": ["01205"],
    "version": "1.0",
}

# Shape of https://thronesdb.com/api/public/cards/ entries (trimmed).
CATALOG = {
    "01001": {
        "code": "01001",
        "name": "A Clash of Kings",
        "type_code": "plot",
        "image_url": "https://thronesdb.com/images/cards/GT01_1.jpg",
    },
    "01205": {
        "code": "01205",
        "name": "Fealty",
        "type_code": "agenda",
        "image_url": "https://thronesdb.com/images/cards/GT01_205B.jpg",
    },
    "00022": {
        "code": "00022",
        "name": "The Knight",
        "type_code": "character",
        "image_url": None,
    },
}


# --- Unit Tests ---

class TestDeckFormatEnum:
    """Test the DeckFormat enum values."""

    def test_thronesdb_json_format_value(self):
        assert DeckFormat.THRONESDB_JSON.value == 'thronesdb_json'

    def test_thronesdb_url_format_value(self):
        assert DeckFormat.THRONESDB_URL.value == 'thronesdb_url'


class TestDecklistURLPattern:
    """Test ThronesDB decklist URL pattern matching."""

    def test_decklist_url_matches(self):
        match = DECKLIST_URL_PATTERN.match("https://thronesdb.com/decklist/view/16782")
        assert match is not None
        assert match.group(1) == "16782"

    def test_decklist_url_with_slug_matches(self):
        match = DECKLIST_URL_PATTERN.match("https://thronesdb.com/decklist/view/1/secrets-and-schemes-1-core-set-1.0")
        assert match is not None
        assert match.group(1) == "1"

    def test_rejects_invalid_urls(self):
        assert not DECKLIST_URL_PATTERN.match("")
        assert not DECKLIST_URL_PATTERN.match("12345")
        assert not DECKLIST_URL_PATTERN.match("https://example.com/decklist/view/12345")
        assert not DECKLIST_URL_PATTERN.match("https://thronesdb.com/deck/view/12345")
        assert not DECKLIST_URL_PATTERN.match("https://thronesdb.com/card/01001")


class TestParseDeckHelper:
    """Test slot expansion into handle_card calls."""

    def test_slots_are_all_handled_in_order(self):
        seen = []
        parse_deck_helper(DECKLIST_JSON["slots"], lambda index, code, quantity: seen.append((index, code, quantity)))

        assert seen == [(1, "01003", 1), (2, "01028", 2), (3, "01205", 1)]

    def test_non_positive_quantities_are_skipped(self, capsys):
        seen = []
        parse_deck_helper({"01003": 0, "01028": 2}, lambda index, code, quantity: seen.append((index, code, quantity)))

        assert seen == [(1, "01028", 2)]
        assert "Skipping" in capsys.readouterr().out

    def test_errors_from_handle_card_are_collected_not_raised(self, capsys):
        def failing_handle_card(index, code, quantity):
            if code == "01003":
                raise ValueError("boom")

        # Should not raise, even though one card fails.
        parse_deck_helper({"01003": 1, "01028": 1}, failing_handle_card)

        assert "Errors:" in capsys.readouterr().out


class TestParseDeck:
    """Test format dispatch (no network)."""

    def test_parse_deck_dispatches_to_json_parser(self):
        seen = []
        parse_deck(json.dumps(DECKLIST_JSON), DeckFormat.THRONESDB_JSON, lambda index, code, quantity: seen.append(code))

        # The agenda is part of slots; the faction card is not a card code.
        assert seen == ["01003", "01028", "01205"]

    def test_parse_deck_dispatches_to_url_parser(self):
        seen = []
        with patch("plugins.game_of_thrones_lcg.deck_formats.fetch_decklist", return_value=DECKLIST_JSON) as mock_fetch:
            parse_deck(
                "https://thronesdb.com/decklist/view/1/secrets-and-schemes-1-core-set-1.0",
                DeckFormat.THRONESDB_URL,
                lambda index, code, quantity: seen.append(code),
            )

        mock_fetch.assert_called_once_with("1")
        assert seen == ["01003", "01028", "01205"]

    def test_url_read_from_file_with_bom(self, tmp_path):
        deck_file = tmp_path / "deck.txt"
        deck_file.write_text("https://thronesdb.com/decklist/view/1\n", encoding="utf-8-sig")

        with patch("plugins.game_of_thrones_lcg.deck_formats.fetch_decklist", return_value=DECKLIST_JSON) as mock_fetch:
            parse_deck(str(deck_file), DeckFormat.THRONESDB_URL, lambda *args: None)

        mock_fetch.assert_called_once_with("1")

    def test_invalid_url_does_not_fetch(self, capsys):
        with patch("plugins.game_of_thrones_lcg.deck_formats.fetch_decklist") as mock_fetch:
            parse_deck("https://thronesdb.com/deck/view/1", DeckFormat.THRONESDB_URL, lambda *args: None)

        mock_fetch.assert_not_called()
        assert "not a valid ThronesDB decklist URL" in capsys.readouterr().out

    def test_unrecognized_format_raises(self):
        with pytest.raises(ValueError):
            parse_deck("{}", "not_a_real_format", lambda *args: None)


class TestFetchCardArt:
    """Test image saving with mocked requests."""

    def test_saves_one_file_per_copy_with_sniffed_extension(self, tmp_path):
        with patch.object(api, "fetch_card_catalog", return_value=CATALOG), \
             patch.object(api, "request_thronesdb", return_value=image_response(image_bytes(300, 418, 'PNG'), 'image/png')):
            api.fetch_card_art(3, "01205", 2, str(tmp_path))

        assert sorted(os.listdir(tmp_path)) == ["3Fealty1.png", "3Fealty2.png"]

    def test_landscape_plot_is_rotated_to_portrait(self, tmp_path):
        with patch.object(api, "fetch_card_catalog", return_value=CATALOG), \
             patch.object(api, "request_thronesdb", return_value=image_response(image_bytes(419, 304))):
            api.fetch_card_art(1, "01001", 1, str(tmp_path))

        assert os.listdir(tmp_path) == ["1AClashofKings1.jpg"]
        with Image.open(tmp_path / "1AClashofKings1.jpg") as img:
            assert img.height > img.width

    def test_non_image_response_raises(self, tmp_path):
        with patch.object(api, "fetch_card_catalog", return_value=CATALOG), \
             patch.object(api, "request_thronesdb", return_value=image_response(b"<html></html>", 'text/html')):
            with pytest.raises(ValueError):
                api.fetch_card_art(1, "01001", 1, str(tmp_path))

        assert os.listdir(tmp_path) == []

    def test_card_without_image_raises(self, tmp_path):
        with patch.object(api, "fetch_card_catalog", return_value=CATALOG):
            with pytest.raises(ValueError):
                api.fetch_card_art(1, "00022", 1, str(tmp_path))

    def test_unknown_card_raises(self, tmp_path):
        with patch.object(api, "fetch_card_catalog", return_value=CATALOG):
            with pytest.raises(ValueError):
                api.fetch_card_art(1, "99999", 1, str(tmp_path))


# --- Integration Tests ---

@pytest.mark.integration
class TestThronesDBAPI:
    """Test ThronesDB public API requests."""

    def test_card_catalog_has_image_urls(self):
        card = fetch_card_catalog().get("01001")
        assert card is not None
        assert card.get("image_url")

    def test_decklist_has_agenda_in_slots(self):
        decklist = fetch_decklist("1")
        assert decklist["slots"]
        for agenda in decklist["agendas"]:
            assert agenda in decklist["slots"]


@pytest.mark.integration
class TestFullFetchWorkflow:
    """Integration tests for the complete card fetching workflow."""

    @pytest.fixture
    def front_dir(self):
        front_dir = tempfile.mkdtemp()
        yield front_dir
        shutil.rmtree(front_dir)

    def test_fetch_deck_from_thronesdb_json(self, front_dir):
        # 01001 is a landscape plot, 01205 (Fealty) is an agenda.
        deck_text = json.dumps({"slots": {"01001": 2, "01205": 1}})

        parse_deck(deck_text, DeckFormat.THRONESDB_JSON, get_handle_card(front_dir))

        front_files = os.listdir(front_dir)
        assert len(front_files) == 3

        for f in front_files:
            with Image.open(os.path.join(front_dir, f)) as img:
                assert img.height > img.width
