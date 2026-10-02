"""
Tests for the Doomtown: Reloaded plugin.
Tests deck format parsing and image fetching from DoomtownDB (dtdb.co).
"""
import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from plugins.doomtown_reloaded import deck_formats, dtdb
from plugins.doomtown_reloaded.deck_formats import DeckFormat, DECK_URL_PATTERN, parse_deck, parse_deck_helper
from plugins.doomtown_reloaded.dtdb import fetch_cards, fetch_dtdb_decklist, get_handle_card

# Real-shaped response of https://dtdb.co/api/decklist/3803 (trimmed)
DECKLIST_RESPONSE = {
    "id": 3803,
    "name": "3/8/10 Law Dogs",
    "creation": "2026-08-01 00:00:00",
    "description": "",
    "username": "example",
    "cards": {
        "24009": 1,  # Law Dogs (outfit)
        "24065": 1,  # Laura Banks
        "24098": 2,  # El Anonimo
        "24258": 1,  # Joker (black)
        "24259": 1,  # Joker (red)
    },
}

# Real-shaped entries of https://dtdb.co/api/cards (trimmed)
CARDS = {
    "24065": {"code": "24065", "title": "Laura Banks", "imagesrc": "/images/cards/en/24065.jpg"},
    "24258": {"code": "24258", "title": "Joker (black)", "imagesrc": "/images/cards/en/24258.jpg"},
}

JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"\x00" * 32


# --- Unit Tests ---

class TestDeckFormatEnum:
    def test_dtdb_url_format_value(self):
        assert DeckFormat.DTDB_URL.value == 'dtdb_url'


class TestDeckURLPattern:
    def test_decklist_url_with_locale_and_slug(self):
        match = DECK_URL_PATTERN.match("https://dtdb.co/en/decklist/3803/3-8-10-law-dogs")
        assert match is not None
        assert match.group(1) == "3803"

    def test_decklist_url_without_locale(self):
        match = DECK_URL_PATTERN.match("https://dtdb.co/decklist/3803")
        assert match is not None
        assert match.group(1) == "3803"

    def test_rejects_invalid_urls(self):
        assert not DECK_URL_PATTERN.match("")
        assert not DECK_URL_PATTERN.match("3803")
        assert not DECK_URL_PATTERN.match("https://example.com/en/decklist/3803")
        assert not DECK_URL_PATTERN.match("https://dtdb.co/en/card/24065")


class TestParseDeckHelper:
    def test_all_cards_are_handled_in_order(self):
        seen = []
        parse_deck_helper(DECKLIST_RESPONSE["cards"], lambda index, code, quantity: seen.append((index, code, quantity)))

        assert seen == [
            (1, "24009", 1),
            (2, "24065", 1),
            (3, "24098", 2),
            (4, "24258", 1),
            (5, "24259", 1),
        ]

    def test_invalid_quantities_are_skipped(self, capsys):
        seen = []
        parse_deck_helper({"24009": 0, "24065": 1}, lambda index, code, quantity: seen.append(code))

        assert seen == ["24065"]
        assert 'Skipping: "24009: 0"' in capsys.readouterr().out

    def test_errors_from_handle_card_are_collected_not_raised(self, capsys):
        def failing_handle_card(index, code, quantity):
            if code == "24065":
                raise ValueError("boom")

        parse_deck_helper({"24065": 1, "24098": 1}, failing_handle_card)

        assert "Errors:" in capsys.readouterr().out


class TestParseDtdbUrl:
    def test_url_is_fetched_by_deck_id(self):
        seen = []
        with patch.object(deck_formats, "fetch_dtdb_decklist", return_value=DECKLIST_RESPONSE) as mock_fetch:
            parse_deck(
                "https://dtdb.co/en/decklist/3803/3-8-10-law-dogs\n",
                DeckFormat.DTDB_URL,
                lambda index, code, quantity: seen.append(code),
            )

        mock_fetch.assert_called_once_with("3803")
        assert seen == list(DECKLIST_RESPONSE["cards"])

    def test_invalid_url_does_not_fetch(self):
        with patch.object(deck_formats, "fetch_dtdb_decklist") as mock_fetch:
            parse_deck("https://example.com/deck/1", DeckFormat.DTDB_URL, lambda *args: None)

        mock_fetch.assert_not_called()

    def test_unrecognized_format_raises(self):
        with pytest.raises(ValueError):
            parse_deck("", "not_a_real_format", lambda *args: None)


class TestFetchCardArt:
    def test_saves_one_file_per_copy(self, tmp_path):
        response = MagicMock(content=JPEG_BYTES, headers={"content-type": "image/jpeg"})

        with patch.object(dtdb, "fetch_cards", return_value=CARDS), \
             patch.object(dtdb, "request_dtdb", return_value=response) as mock_request:
            dtdb.fetch_card_art(3, "24065", 2, str(tmp_path))

        mock_request.assert_called_once_with("https://dtdb.co/images/cards/en/24065.jpg")
        assert sorted(os.listdir(tmp_path)) == ["3LauraBanks1.jpg", "3LauraBanks2.jpg"]

    def test_non_image_response_raises(self, tmp_path):
        response = MagicMock(content=b"<html></html>", headers={"content-type": "text/html; charset=UTF-8"})

        with patch.object(dtdb, "fetch_cards", return_value=CARDS), \
             patch.object(dtdb, "request_dtdb", return_value=response):
            with pytest.raises(ValueError):
                dtdb.fetch_card_art(1, "24065", 1, str(tmp_path))

        assert os.listdir(tmp_path) == []

    def test_unknown_code_raises(self, tmp_path):
        with patch.object(dtdb, "fetch_cards", return_value=CARDS):
            with pytest.raises(ValueError):
                dtdb.fetch_card_art(1, "99999", 1, str(tmp_path))


# --- Integration Tests ---

@pytest.mark.integration
class TestDtdbAPI:
    def test_card_list_has_images(self):
        card = fetch_cards()["24065"]
        assert card["title"] == "Laura Banks"
        assert card["imagesrc"] == "/images/cards/en/24065.jpg"

    def test_decklist_has_cards(self):
        deck = fetch_dtdb_decklist("1")
        assert deck["cards"]["01001"] == 1


@pytest.mark.integration
class TestFullFetchWorkflow:
    @pytest.fixture
    def front_dir(self):
        front_dir = tempfile.mkdtemp()
        yield front_dir
        shutil.rmtree(front_dir)

    def test_fetch_cards_by_code(self, front_dir):
        handle_card = get_handle_card(front_dir)
        handle_card(1, "24065", 2)  # Laura Banks
        handle_card(2, "24009", 1)  # Law Dogs (outfit)

        front_files = sorted(os.listdir(front_dir))
        assert len(front_files) == 3

        for f in front_files:
            with Image.open(os.path.join(front_dir, f)) as img:
                img.verify()
