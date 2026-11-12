"""
Tests for the Star Wars: The Card Game plugin.
Tests deck format parsing and image fetching from SWLCGDB.
"""
import os
from io import BytesIO
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from plugins.star_wars_lcg import swlcgdb
from plugins.star_wars_lcg.deck_formats import DECK_URL_PATTERN, DeckFormat, parse_deck, parse_deck_helper
from plugins.star_wars_lcg.swlcgdb import get_handle_card


# Trimmed from https://swlcgdb.com/api/decks/387
DECK_JSON = {
    "id": 387,
    "name": "Black Squadron Pilots",
    "cards": [
        {"id": 26, "name": "\"Howlrunner\"", "block": 255, "card_block_id": 5, "card_type": "Unit", "quantity": 2},
        {"id": 342, "name": "Stay on Target", "block": 143, "card_block_id": 57, "card_type": "Event", "quantity": 6},
    ],
}

# Trimmed from https://swlcgdb.com/api/card_blocks/5
CARD_BLOCK_JSON = {
    "id": 5,
    "block": 255,
    "name": "Cloud Cover",
    "cards": [
        {"id": 25, "card_block_id": 5, "name": "Cloud Cover", "block": 255, "block_number": 1},
        {"id": 26, "card_block_id": 5, "name": "\"Howlrunner\"", "block": 255, "block_number": 2},
    ],
}


class TestDeckURLPattern:
    def test_deck_url_matches(self):
        match = DECK_URL_PATTERN.match("https://swlcgdb.com/decks/387")
        assert match is not None
        assert match.group(1) == "387"

    def test_rejects_invalid_urls(self):
        assert not DECK_URL_PATTERN.match("")
        assert not DECK_URL_PATTERN.match("387")
        assert not DECK_URL_PATTERN.match("https://swlcgdb.com/cards/387")
        assert not DECK_URL_PATTERN.match("https://example.com/decks/387")


class TestParseDeck:
    def test_cards_are_handled_with_quantities(self, capsys):
        seen = []
        parse_deck_helper(DECK_JSON, lambda index, card, quantity: seen.append((index, card["id"], quantity)))

        assert seen == [(1, 26, 2), (2, 342, 6)]
        assert "Index: 1, quantity: 2, id: 26" in capsys.readouterr().out

    def test_invalid_entries_are_skipped(self, capsys):
        seen = []
        parse_deck_helper({"cards": [{"name": "Broken", "quantity": 1}]}, lambda *args: seen.append(args))

        assert seen == []
        assert 'Skipping: "Broken"' in capsys.readouterr().out

    def test_errors_from_handle_card_are_collected_not_raised(self, capsys):
        def failing_handle_card(index, card, quantity):
            raise ValueError("boom")

        parse_deck_helper(DECK_JSON, failing_handle_card)

        assert "Errors:" in capsys.readouterr().out

    def test_url_fetches_deck(self):
        seen = []
        with patch("plugins.star_wars_lcg.deck_formats.fetch_deck", return_value=DECK_JSON) as mock_fetch:
            parse_deck("https://swlcgdb.com/decks/387\n", DeckFormat.SWLCGDB_URL, lambda index, card, quantity: seen.append(card["id"]))

        mock_fetch.assert_called_once_with("387")
        assert seen == [26, 342]

    def test_invalid_url_does_not_fetch(self):
        with patch("plugins.star_wars_lcg.deck_formats.fetch_deck") as mock_fetch:
            parse_deck("https://example.com/decks/387", DeckFormat.SWLCGDB_URL, lambda *args: None)

        mock_fetch.assert_not_called()

    def test_unrecognized_format_raises(self):
        with pytest.raises(ValueError):
            parse_deck("", "not_a_real_format", lambda *args: None)


def jpeg_bytes(width, height):
    buffer = BytesIO()
    Image.new("RGB", (width, height)).save(buffer, format="JPEG")
    return buffer.getvalue()


class TestFetchCard:
    def test_image_url_uses_block_number_and_saves_copies(self, tmp_path):
        image_response = MagicMock(headers={"content-type": "image/jpeg"}, content=jpeg_bytes(344, 480))

        with patch.object(swlcgdb, "fetch_card_block", return_value=CARD_BLOCK_JSON), \
             patch.object(swlcgdb, "request_swlcgdb", return_value=image_response) as mock_request:
            swlcgdb.fetch_card(3, 2, DECK_JSON["cards"][0], str(tmp_path))

        mock_request.assert_called_once_with("https://swlcg-card-images.nyc3.digitaloceanspaces.com/cards/255-2.jpg")
        assert sorted(os.listdir(tmp_path)) == ["3Howlrunner1.jpg", "3Howlrunner2.jpg"]

    def test_landscape_objective_is_rotated_to_portrait(self, tmp_path):
        image_response = MagicMock(headers={"content-type": "image/jpeg"}, content=jpeg_bytes(669, 480))

        with patch.object(swlcgdb, "fetch_card_block", return_value=CARD_BLOCK_JSON),              patch.object(swlcgdb, "request_swlcgdb", return_value=image_response):
            swlcgdb.fetch_card(1, 1, DECK_JSON["cards"][0], str(tmp_path))

        with Image.open(tmp_path / "1Howlrunner1.jpg") as img:
            assert img.size == (480, 669)

    def test_non_image_response_raises(self, tmp_path):
        xml_response = MagicMock(headers={"content-type": "application/xml"}, content=b"<Error/>")

        with patch.object(swlcgdb, "fetch_card_block", return_value=CARD_BLOCK_JSON), \
             patch.object(swlcgdb, "request_swlcgdb", return_value=xml_response):
            with pytest.raises(ValueError):
                swlcgdb.fetch_card(1, 1, DECK_JSON["cards"][0], str(tmp_path))

        assert os.listdir(tmp_path) == []

    def test_card_missing_from_block_raises(self, tmp_path):
        with patch.object(swlcgdb, "fetch_card_block", return_value=CARD_BLOCK_JSON):
            with pytest.raises(ValueError):
                swlcgdb.fetch_card(1, 1, DECK_JSON["cards"][1], str(tmp_path))


# --- Integration Tests ---

@pytest.mark.integration
class TestFullFetchWorkflow:
    @pytest.fixture
    def front_dir(self):
        front_dir = tempfile.mkdtemp()
        yield front_dir
        shutil.rmtree(front_dir)

    def test_fetch_single_card(self, front_dir):
        card = {"id": 26, "name": "\"Howlrunner\"", "card_block_id": 5}

        get_handle_card(front_dir)(1, card, 2)

        files = os.listdir(front_dir)
        assert len(files) == 2
        for f in files:
            with Image.open(os.path.join(front_dir, f)) as img:
                assert img.height > img.width
