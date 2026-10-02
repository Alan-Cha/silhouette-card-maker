"""
Tests for the Alpha Clash plugin.
Tests deck format parsing and image fetching from DeckPlanet.
"""
import os
import shutil
import tempfile
from unittest.mock import Mock, patch

import pytest
from PIL import Image

from plugins.alpha_clash.deck_formats import DeckFormat, parse_deck, parse_deckplanet
from plugins.alpha_clash.deckplanet import request_deckplanet, get_handle_card, CARD_ART_URL_TEMPLATE


def collect(deck_text, parser=parse_deckplanet):
    parsed_cards = []
    def collect_card(index, card_id, quantity):
        parsed_cards.append((index, card_id, quantity))
    parser(deck_text, collect_card)
    return parsed_cards


# --- Unit Tests for Deck Format Parsing ---

class TestDeckplanetFormat:
    """Test DeckPlanet format parsing."""

    def test_parse_deckplanet(self):
        """Test parsing a DeckPlanet export with Contender, alternate art, and sideboard."""
        deck_text = """The Absence, Voice of the Void [AC7-001]
3 Sharpshooter Moxie [AC1-019]
3 Haven, Bountiful Collector [AC1-095_AA]
4 Low Earth Orbit [AC2-025]
---Sideboard---
4 Marcus, Ghost of the Gambit [PG-003]"""

        assert collect(deck_text) == [
            (1, 'AC7-001', 1),
            (2, 'AC1-019', 3),
            (3, 'AC1-095_AA', 3),
            (4, 'AC2-025', 4),
            (5, 'PG-003', 4),
        ]

    def test_parse_deckplanet_punctuation_and_crlf(self):
        """Test names with punctuation and Windows line endings."""
        deck_text = "Webber, Demolitions Agent [ST3-001]\r\n4 Moxie's Heavy Power Armor [AC1-018]\r\n4 Suit Up! [AC3-027]\r\n"

        assert collect(deck_text) == [(1, 'ST3-001', 1), (2, 'AC1-018', 4), (3, 'AC3-027', 4)]

    def test_parse_deck_dispatch(self):
        """Test dispatching through parse_deck."""
        assert collect('2 Tactical Vest [AC3-023]', lambda t, h: parse_deck(t, DeckFormat.DECKPLANET, h)) == [(1, 'AC3-023', 2)]

    def test_parse_deck_unknown_format(self):
        """Test that an unknown format raises ValueError."""
        with pytest.raises(ValueError):
            parse_deck('2 Tactical Vest [AC3-023]', 'unknown', lambda *args: None)


# --- Unit Tests for Image Saving ---

def fake_response(content=b'RIFF\x00\x00\x00\x00WEBPVP8 ', content_type='image/webp'):
    response = Mock()
    response.content = content
    response.headers = {'content-type': content_type}
    return response


class TestFetchCard:
    """Test image saving with mocked requests."""

    @pytest.fixture
    def temp_dirs(self):
        front_dir = tempfile.mkdtemp()
        back_dir = tempfile.mkdtemp()
        yield front_dir, back_dir
        shutil.rmtree(front_dir)
        shutil.rmtree(back_dir)

    def test_saves_one_file_per_copy(self, temp_dirs):
        front_dir, back_dir = temp_dirs
        with patch('plugins.alpha_clash.deckplanet.request_deckplanet', return_value=fake_response()) as request:
            get_handle_card(front_dir, back_dir)(2, 'AC1-001', 3)

        request.assert_called_once_with(CARD_ART_URL_TEMPLATE.format(card_id='AC1-001'))
        assert sorted(os.listdir(front_dir)) == ['2AC1-0011.webp', '2AC1-0012.webp', '2AC1-0013.webp']
        assert os.listdir(back_dir) == []

    def test_saves_back_of_double_faced_card(self, temp_dirs):
        front_dir, back_dir = temp_dirs
        with patch('plugins.alpha_clash.deckplanet.request_deckplanet', return_value=fake_response()) as request:
            get_handle_card(front_dir, back_dir)(1, 'AC4-002', 1)

        assert request.call_args_list[1].args[0] == CARD_ART_URL_TEMPLATE.format(card_id='AC4-060')
        assert os.listdir(front_dir) == os.listdir(back_dir) == ['1AC4-0021.webp']

    def test_rejects_non_image_response(self, temp_dirs):
        front_dir, back_dir = temp_dirs
        with patch('plugins.alpha_clash.deckplanet.request_deckplanet', return_value=fake_response(b'<html>', 'text/html')):
            with pytest.raises(ValueError):
                get_handle_card(front_dir, back_dir)(1, 'AC1-001', 1)

        assert os.listdir(front_dir) == []


# --- Integration Tests for API and Image Fetching ---

@pytest.mark.integration
class TestDeckplanetAPI:
    """Test DeckPlanet image requests."""

    def test_deckplanet_image_availability(self):
        """Test that Alpha Clash card images are available."""
        response = request_deckplanet(CARD_ART_URL_TEMPLATE.format(card_id='DB1-109'))
        assert response.status_code == 200
        assert response.headers['content-type'].startswith('image/')


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

    def test_fetch_deckplanet(self, temp_dirs):
        """Test fetching a Contender and a double-faced Contender."""
        front_dir, back_dir = temp_dirs

        deck_text = """Webber, Demolitions Agent [ST3-001]
1 Shadowlight, Bright Beacon [AC4-002]"""

        parse_deck(deck_text, DeckFormat.DECKPLANET, get_handle_card(front_dir, back_dir))

        assert sorted(os.listdir(front_dir)) == ['1ST3-0011.webp', '2AC4-0021.webp']
        assert os.listdir(back_dir) == ['2AC4-0021.webp']

        for directory in (front_dir, back_dir):
            for f in os.listdir(directory):
                with Image.open(os.path.join(directory, f)) as image:
                    image.verify()
