"""
Tests for the Battle Spirits Saga plugin.
Tests deck format parsing and image fetching from the official Battle Spirits Saga site and bssdb.dev.
"""
import os
import shutil
import tempfile
import pytest
from PIL import Image

from plugins.battle_spirits_saga import battle_spirits_saga
from plugins.battle_spirits_saga.deck_formats import (
    DeckFormat,
    parse_deck,
    parse_bssdb,
    parse_bssdb_tts,
)
from plugins.battle_spirits_saga.battle_spirits_saga import (
    get_handle_card,
    get_image_key,
    request_battle_spirits_saga,
)


def collect_cards(parse, deck_text):
    parsed_cards = []
    def collect_card(index, card_code, quantity):
        parsed_cards.append({
            'index': index,
            'card_code': card_code,
            'quantity': quantity
        })

    parse(deck_text, collect_card)
    return parsed_cards


# --- Unit Tests for Deck Format Parsing ---

class TestBssdbFormat:
    """Test bssdb.dev text export parsing."""

    def test_parse_bssdb(self):
        """Test parsing main deck and sideboard sections."""
        deck_text = """=== Main Deck ===
3x BSS01-039-p1: Beldegor of the Dark World Seven
4x BSS01-118: Starblessed Draw
3x ST02-002: Dragonaga Assassin

=== Sideboard ===
2x PR-001: Ferrarl Slash
"""

        parsed_cards = collect_cards(parse_bssdb, deck_text)

        assert parsed_cards == [
            {'index': 1, 'card_code': 'BSS01-039-p1', 'quantity': 3},
            {'index': 2, 'card_code': 'BSS01-118', 'quantity': 4},
            {'index': 3, 'card_code': 'ST02-002', 'quantity': 3},
            {'index': 4, 'card_code': 'PR-001', 'quantity': 2},
        ]

    def test_parse_deck_dispatch(self):
        """Test parse_deck dispatches to the bssdb parser."""
        parsed_cards = collect_cards(
            lambda text, handle: parse_deck(text, DeckFormat.BSSDB, handle),
            "4x BSS07B-001: Undead Dragon Bone Titanoks"
        )

        assert parsed_cards == [{'index': 1, 'card_code': 'BSS07B-001', 'quantity': 4}]

    def test_unrecognized_format(self):
        """Test parse_deck rejects unknown formats."""
        with pytest.raises(ValueError):
            parse_deck("4x BSS01-118: Starblessed Draw", 'unknown', lambda *args: None)


class TestBssdbTTSFormat:
    """Test bssdb.dev Dexef's Tabletop Simulator export parsing."""

    def test_parse_bssdb_tts(self):
        """Test that repeated codes are counted into quantities."""
        deck_text = """=== Main Deck ===
[BSS01-039_p1,BSS01-039_p1,BSS01-039_p1,BSS01-118,BSS01-118,ST02-002]

=== Sideboard ===
[PR-001,PR-001]
"""

        parsed_cards = collect_cards(parse_bssdb_tts, deck_text)

        assert parsed_cards == [
            {'index': 1, 'card_code': 'BSS01-039_p1', 'quantity': 3},
            {'index': 2, 'card_code': 'BSS01-118', 'quantity': 2},
            {'index': 3, 'card_code': 'ST02-002', 'quantity': 1},
            {'index': 4, 'card_code': 'PR-001', 'quantity': 2},
        ]


class TestImageKey:
    """Test conversion from card codes to image names."""

    def test_get_image_key(self):
        assert get_image_key('BSS01-039-p1') == 'BSS01-039_p1'
        assert get_image_key('BSS01-039_p1') == 'BSS01-039_p1'
        assert get_image_key('BSS07B-X01') == 'BSS07B-X01'


class FakeResponse:
    def __init__(self, status_code, content=b'', content_type='image/png'):
        self.status_code = status_code
        self.content = content
        self.headers = {'content-type': content_type}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f'HTTP {self.status_code}')


class TestFetchCard:
    """Test saving images with mocked requests."""

    @pytest.fixture
    def front_dir(self):
        front_dir = tempfile.mkdtemp()
        yield front_dir
        shutil.rmtree(front_dir)

    def test_falls_back_to_bssdb(self, front_dir, monkeypatch):
        """Test that a card missing from the official site is fetched from bssdb.dev."""
        png = b'\x89PNG\r\n\x1a\n' + b'\x00' * 32
        requested = []
        def fake_request(url):
            requested.append(url)
            return FakeResponse(404) if 'battlespirits-saga.com' in url else FakeResponse(200, png)
        monkeypatch.setattr(battle_spirits_saga, 'request_battle_spirits_saga', fake_request)

        get_handle_card(front_dir)(1, 'BSS07B-001', 2)

        assert requested == [
            'https://www.battlespirits-saga.com/images/cards/card/BSS07B-001.png',
            'https://www.bssdb.dev/cards/bss/BSS07B-001.png',
        ]
        assert sorted(os.listdir(front_dir)) == ['1BSS07B-0011.png', '1BSS07B-0012.png']

    def test_rejects_non_image(self, front_dir, monkeypatch):
        """Test that a non-image response is not saved."""
        monkeypatch.setattr(
            battle_spirits_saga,
            'request_battle_spirits_saga',
            lambda url: FakeResponse(200, b'<html></html>', 'text/html')
        )

        with pytest.raises(ValueError):
            get_handle_card(front_dir)(1, 'BSS01-118', 1)
        assert os.listdir(front_dir) == []


# --- Integration Tests for API and Image Fetching ---

@pytest.mark.integration
class TestBattleSpiritsSagaAPI:
    """Test Battle Spirits Saga image server requests."""

    def test_official_image_availability(self):
        """Test that the official card image server is available and responding."""
        response = request_battle_spirits_saga('https://www.battlespirits-saga.com/images/cards/card/BSS01-118.png')
        assert response.status_code == 200
        assert response.headers['content-type'].startswith('image/')


@pytest.mark.integration
class TestFullFetchWorkflow:
    """Integration tests for the complete card fetching workflow."""

    @pytest.fixture
    def front_dir(self):
        front_dir = tempfile.mkdtemp()
        yield front_dir
        shutil.rmtree(front_dir)

    def test_fetch_bssdb_with_quantity(self, front_dir):
        """Test fetching an official parallel card and a bssdb.dev-only card."""
        deck_text = """=== Main Deck ===
2x BSS01-039-p1: Beldegor of the Dark World Seven
1x BSS07B-001: Undead Dragon Bone Titanoks"""

        parse_deck(deck_text, DeckFormat.BSSDB, get_handle_card(front_dir))

        files = sorted(os.listdir(front_dir))
        assert files == ['1BSS01-039_p11.png', '1BSS01-039_p12.png', '2BSS07B-0011.png']

        for f in files:
            with Image.open(os.path.join(front_dir, f)) as image:
                image.load()
