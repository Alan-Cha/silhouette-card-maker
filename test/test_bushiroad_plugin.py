"""
Tests for the Bushiroad plugin (Cardfight Vanguard, Weiss Schwarz, etc.).
Tests deck URL pattern matching and image fetching from Bushiroad CDNs.
"""
import os
import shutil
import tempfile
import pytest
from unittest.mock import MagicMock, patch

from plugins.bushiroad.bushiroad import request_bushiroad, GameTitle, resolve_image_url, get_handle_card, fetch_decklist
from plugins.bushiroad.deck_formats import DeckFormat, parse_deck


# --- Unit Tests ---

class TestBushiroadURLFormat:
    """Test Bushiroad Decklog URL format parsing."""

    def test_decklog_en_url_pattern_matches(self):
        """Test that valid English Decklog URLs are detected."""
        import re
        pattern = re.compile(r'https?://decklog(?:-en)?\.bushiroad\.com/view/(\w+)\s*')

        assert pattern.match("https://decklog-en.bushiroad.com/view/ABCDEF")
        assert pattern.match("https://decklog-en.bushiroad.com/view/12345")

    def test_decklog_jp_url_pattern_matches(self):
        """Test that valid Japanese Decklog URLs are detected."""
        import re
        pattern = re.compile(r'https?://decklog(?:-en)?\.bushiroad\.com/view/(\w+)\s*')

        assert pattern.match("https://decklog.bushiroad.com/view/ABCDEF")

    def test_decklog_url_pattern_rejects_invalid(self):
        """Test that invalid lines are rejected."""
        import re
        pattern = re.compile(r'https?://decklog(?:-en)?\.bushiroad\.com/view/(\w+)\s*')

        assert not pattern.match("")
        assert not pattern.match("https://example.com/view/ABCDEF")
        assert not pattern.match("ABCDEF")

    def test_decklog_url_extracts_deck_code(self):
        """Test that the deck code is correctly extracted from a URL."""
        import re
        pattern = re.compile(r'https?://decklog(?:-en)?\.bushiroad\.com/view/(\w+)\s*')

        match = pattern.match("https://decklog-en.bushiroad.com/view/ABCDEF123")
        assert match is not None
        assert match.group(1) == "ABCDEF123"

    def test_resolve_image_url_vanguard(self):
        """Test that Cardfight Vanguard image URLs are resolved correctly."""
        url = resolve_image_url(GameTitle.CARDFIGHT_VANGUARD, "V-BT01/en_V-BT01-001EN.png")
        assert "en.cf-vanguard.com" in url
        assert "V-BT01/en_V-BT01-001EN.png" in url

    def test_resolve_image_url_weiss_schwarz(self):
        """Test that Weiss Schwarz image URLs are resolved correctly."""
        url = resolve_image_url(GameTitle.WEISS_SCHWARZ, "SAO/EN-W02-E001.jpg")
        assert "en.ws-tcg.com" in url
        assert "SAO/EN-W02-E001.jpg" in url

    def test_resolve_image_url_unsupported_raises(self):
        """Test that unsupported game title raises ValueError."""
        with pytest.raises(ValueError):
            resolve_image_url("Unsupported Game", "some_image.png")

    def test_resolve_image_url_jp_hosts(self):
        """Test that Japanese Deck Log decks use the Japanese image hosts."""
        assert resolve_image_url(GameTitle.CARDFIGHT_VANGUARD, "V-SS10/vss10_029.png", "decklog") ==             "https://cf-vanguard.com/wordpress/wp-content/images/cardlist/V-SS10/vss10_029.png"
        assert resolve_image_url(GameTitle.WEISS_SCHWARZ, "a/anm_w138/anm_w138_001.png", "decklog") ==             "https://ws-tcg.com/wordpress/wp-content/images/cardlist/a/anm_w138/anm_w138_001.png"


def _mock_deck_response(game_title_id, img="SET/card.png"):
    response = MagicMock()
    response.json.return_value = {
        "game_title_id": game_title_id,
        "list": [{"name": "Card", "num": 1, "img": img}],
    }
    return response


class TestBushiroadHostSelection:
    """Test that the Deck Log host is taken from the URL."""

    @patch("plugins.bushiroad.bushiroad.request_bushiroad")
    def test_bare_code_defaults_to_en(self, mock_request):
        mock_request.return_value = _mock_deck_response(1)
        game_title, _ = fetch_decklist("1HF6L")
        mock_request.assert_called_once_with(
            "https://decklog-en.bushiroad.com/system/app/api/view/1HF6L", "https://decklog-en.bushiroad.com/")
        assert game_title == GameTitle.CARDFIGHT_VANGUARD

    @patch("plugins.bushiroad.bushiroad.request_bushiroad")
    def test_jp_game_title_ids(self, mock_request):
        """Japanese Deck Log uses different game title IDs than English."""
        mock_request.return_value = _mock_deck_response(13)
        game_title, _ = fetch_decklist("ABCDE", "decklog")
        assert game_title == GameTitle.GODZILLA

        # ID 7 is Godzilla on EN but a different, unsupported game on JP
        mock_request.return_value = _mock_deck_response(7)
        with pytest.raises(ValueError):
            fetch_decklist("ABCDE", "decklog")

    @pytest.mark.parametrize("url,api_url,image_url", [
        ("https://decklog-en.bushiroad.com/view/1HF6L",
         "https://decklog-en.bushiroad.com/system/app/api/view/1HF6L",
         "https://en.cf-vanguard.com/wordpress/wp-content/images/cardlist/SET/card.png"),
        ("https://decklog.bushiroad.com/view/1HF6L",
         "https://decklog.bushiroad.com/system/app/api/view/1HF6L",
         "https://cf-vanguard.com/wordpress/wp-content/images/cardlist/SET/card.png"),
    ])
    @patch("plugins.bushiroad.bushiroad.request_bushiroad")
    def test_url_selects_host(self, mock_request, url, api_url, image_url):
        mock_request.return_value = _mock_deck_response(1)
        handle_card = MagicMock()
        parse_deck(url, DeckFormat.BUSHIROAD_URL, handle_card)
        assert mock_request.call_args[0][0] == api_url
        handle_card.assert_called_once_with(1, "Card", image_url, "", 1)

    @patch("plugins.bushiroad.bushiroad.request_bushiroad")
    def test_bare_code_line_is_skipped(self, mock_request):
        """Bare codes are ambiguous between EN and JP Deck Log, so they are not guessed."""
        handle_card = MagicMock()
        parse_deck("1HF6L", DeckFormat.BUSHIROAD_URL, handle_card)
        mock_request.assert_not_called()
        handle_card.assert_not_called()

    @pytest.mark.parametrize("name,file_name", [
        ("妖魔忍竜・黄昏 ハンゾウ", "V-SS10/029"),
        ("Sealed Blaze of Arbitration", "Sealed Blaze of Arbitration"),
    ])
    @patch("plugins.bushiroad.bushiroad.request_bushiroad")
    def test_jp_name_uses_card_number(self, mock_request, name, file_name):
        """Names without Latin characters fall back to the card number for filenames."""
        response = MagicMock()
        response.json.return_value = {
            "game_title_id": 1,
            "list": [{"name": name, "num": 1, "img": "SET/card.png", "card_number": "V-SS10/029"}],
        }
        mock_request.return_value = response
        handle_card = MagicMock()
        parse_deck("https://decklog.bushiroad.com/view/1HF6L", DeckFormat.BUSHIROAD_URL, handle_card)
        assert handle_card.call_args[0][1] == file_name


# --- Integration Tests ---

@pytest.mark.integration
class TestBushiroadAPI:
    """Test Bushiroad Decklog API requests."""

    def test_decklog_server_availability(self):
        """Test that the Decklog server is available."""
        response = request_bushiroad("https://decklog-en.bushiroad.com/")
        assert response.status_code == 200


@pytest.mark.integration
class TestFullFetchWorkflow:
    """Integration tests for the complete card fetching workflow."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for test output."""
        front_dir = tempfile.mkdtemp()
        back_dir = tempfile.mkdtemp()
        yield front_dir, back_dir
        shutil.rmtree(front_dir)
        shutil.rmtree(back_dir)

    def test_fetch_deck_from_decklog(self, temp_dirs):
        """Test fetching cards from a Bushiroad Decklog deck URL."""
        front_dir, back_dir = temp_dirs

        deck_text = "https://decklog-en.bushiroad.com/view/1HF6L"

        handle_card = get_handle_card(front_dir, back_dir)
        parse_deck(deck_text, DeckFormat.BUSHIROAD_URL, handle_card)

        files = os.listdir(front_dir)
        assert len(files) >= 1

        for f in files:
            file_path = os.path.join(front_dir, f)
            assert os.path.getsize(file_path) > 0

    def test_fetch_deck_from_jp_decklog(self, temp_dirs):
        """Test that a Japanese Deck Log URL fetches the Japanese deck and images."""
        front_dir, back_dir = temp_dirs

        game_title, deck = fetch_decklist("1HF6L", "decklog")
        en_game_title, en_deck = fetch_decklist("1HF6L")
        assert game_title == GameTitle.CARDFIGHT_VANGUARD
        assert [c.get("img") for c in deck] != [c.get("img") for c in en_deck]

        handle_card = get_handle_card(front_dir, back_dir)
        parse_deck("https://decklog.bushiroad.com/view/1HF6L", DeckFormat.BUSHIROAD_URL, handle_card)

        files = os.listdir(front_dir)
        assert len(files) >= 1
        for f in files:
            assert os.path.getsize(os.path.join(front_dir, f)) > 0
