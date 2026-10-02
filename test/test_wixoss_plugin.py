"""
Tests for the WIXOSS plugin.
Tests wixosstcg.eu deck page parsing and image fetching.
"""
import os
import shutil
import tempfile
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from plugins.wixoss.deck_formats import (
    DeckFormat,
    parse_deck,
    parse_wixosstcg_url,
    extract_wixosstcg_cards,
)
from plugins.wixoss.wixoss import fetch_card, get_handle_card


# Trimmed from https://www.wixosstcg.eu/deck/19408/Sorasaki_Hina
DECK_PAGE_HTML = """
<div class="row">
    <div class="col-md-5">
        <strong>LRIG DECK</strong>
            <div Class="rowlist">
                <div Class="colqta col-xs-1">1</div><div class="colcod col-xs-2">WXDi-CP02-005[EN]</div><div class="colname col-xs-6"><a href="#" class="viscarta" data-id="2158">General Student Council</a></div><div class="coltype col-xs-3 hidden-xs">PIECE</div>
            </div>
            <div Class="rowlist">
                <div Class="colqta col-xs-1">1</div><div class="colcod col-xs-2">WXDi-CP02-030[EN]</div><div class="colname col-xs-6"><a href="#" class="viscarta" data-id="2183">C＆C &amp; Friends</a></div><div class="coltype col-xs-3 hidden-xs">ARTS</div>
            </div>
    </div>
    <div class="col-md-7">
        <strong>MAIN</strong>
            <div Class="rowlist">
                <div Class="colqta col-xs-1">4</div><div class="colcod col-xs-2">WXDi-CP02-103[EN]</div><div class="colname col-xs-6"><a href="#" class="viscarta" data-id="2256">Activating the Story</a></div><div class="coltype col-xs-3 hidden-xs">SPELL</div>
            </div>
    </div>
</div>
"""


def collect():
    parsed_cards = []
    def collect_card(index, card_number, quantity):
        parsed_cards.append({'index': index, 'card_number': card_number, 'quantity': quantity})
    return parsed_cards, collect_card


def image_bytes(width, height):
    buffer = BytesIO()
    Image.new('RGB', (width, height)).save(buffer, format='JPEG')
    return buffer.getvalue()


def image_response(content, content_type='image/jpeg'):
    response = MagicMock()
    response.content = content
    response.headers = {'content-type': content_type}
    return response


# --- Unit Tests for Deck Format Parsing ---

class TestWixosstcgUrlFormat:
    """Test wixosstcg.eu deck URL format parsing."""

    def test_extract_cards_from_both_sections(self):
        cards = extract_wixosstcg_cards(DECK_PAGE_HTML)

        assert cards == [
            ('WXDi-CP02-005[EN]', 1, 'General Student Council'),
            ('WXDi-CP02-030[EN]', 1, 'C＆C & Friends'),
            ('WXDi-CP02-103[EN]', 4, 'Activating the Story'),
        ]

    @patch('plugins.wixoss.deck_formats.fetch_deck_page', return_value=DECK_PAGE_HTML)
    def test_parse_url(self, mock_fetch):
        parsed_cards, collect_card = collect()

        parse_wixosstcg_url('https://www.wixosstcg.eu/deck/19408/Sorasaki_Hina', collect_card)

        mock_fetch.assert_called_once_with('https://www.wixosstcg.eu/deck/19408/Sorasaki_Hina')
        assert [c['index'] for c in parsed_cards] == [1, 2, 3]
        assert parsed_cards[2]['card_number'] == 'WXDi-CP02-103[EN]'
        assert parsed_cards[2]['quantity'] == 4

    @patch('plugins.wixoss.deck_formats.fetch_deck_page', return_value=DECK_PAGE_HTML)
    def test_skips_non_deck_lines(self, mock_fetch, capsys):
        parsed_cards, collect_card = collect()

        parse_deck('https://example.com/deck/1\nnot a url', DeckFormat.WIXOSSTCG_URL, collect_card)

        mock_fetch.assert_not_called()
        assert parsed_cards == []
        assert 'Skipping: "not a url"' in capsys.readouterr().out

    @patch('plugins.wixoss.deck_formats.fetch_deck_page', return_value=DECK_PAGE_HTML)
    def test_card_errors_are_collected(self, mock_fetch, capsys):
        def failing_card(index, card_number, quantity):
            raise ValueError('boom')

        parse_wixosstcg_url('https://www.wixosstcg.eu/deck/19408/Sorasaki_Hina', failing_card)

        assert 'Errors:' in capsys.readouterr().out

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError):
            parse_deck('', 'invalid', lambda *args: None)


# --- Unit Tests for Image Saving ---

class TestFetchCard:
    """Test card image saving with mocked requests."""

    @pytest.fixture
    def front_dir(self):
        front_dir = tempfile.mkdtemp()
        yield front_dir
        shutil.rmtree(front_dir)

    @patch('plugins.wixoss.wixoss.request_wixoss')
    def test_saves_one_file_per_copy(self, mock_request, front_dir):
        mock_request.return_value = image_response(image_bytes(75, 105))

        fetch_card(3, 2, 'WXDi-CP02-103[EN]', front_dir)

        assert mock_request.call_args[0][0] == 'https://www.takaratomy.co.jp/products/en.wixoss/card/thumb/WXDi-CP02-103%5BEN%5D.jpg'
        assert sorted(os.listdir(front_dir)) == ['3WXDi-CP02-103EN1.jpg', '3WXDi-CP02-103EN2.jpg']

    @patch('plugins.wixoss.wixoss.request_wixoss')
    def test_rotates_landscape_piece(self, mock_request, front_dir):
        mock_request.return_value = image_response(image_bytes(105, 75))

        fetch_card(1, 1, 'WXDi-CP02-005[EN]', front_dir)

        assert Image.open(os.path.join(front_dir, '1WXDi-CP02-005EN1.jpg')).size == (75, 105)

    @patch('plugins.wixoss.wixoss.request_wixoss')
    def test_rejects_non_image(self, mock_request, front_dir):
        mock_request.return_value = image_response(b'<html></html>', 'text/html')

        with pytest.raises(ValueError):
            fetch_card(1, 1, 'WXDi-CP02-005[EN]', front_dir)

        assert os.listdir(front_dir) == []


# --- Integration Tests ---

@pytest.mark.integration
class TestFullFetchWorkflow:
    """Integration tests for the complete card fetching workflow."""

    @pytest.fixture
    def front_dir(self):
        front_dir = tempfile.mkdtemp()
        yield front_dir
        shutil.rmtree(front_dir)

    def test_fetch_single_card(self, front_dir):
        handle_card = get_handle_card(front_dir)
        handle_card(1, 'WXDi-P01-001[EN]', 1)

        files = os.listdir(front_dir)
        assert len(files) == 1
        Image.open(os.path.join(front_dir, files[0])).verify()

    def test_fetch_deck_page(self):
        from plugins.wixoss.wixoss import fetch_deck_page

        cards = extract_wixosstcg_cards(fetch_deck_page('https://www.wixosstcg.eu/deck/19427/Carnival_P15'))

        assert sum(quantity for _, quantity, _ in cards) == 52
