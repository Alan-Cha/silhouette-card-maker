"""
Tests for the Force of Will plugin.
Tests deck format parsing and image fetching from fowtcg.com.
"""
import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from plugins.force_of_will import fowtcg
from plugins.force_of_will.deck_formats import DeckFormat, parse_deck, parse_fow
from plugins.force_of_will.fowtcg import Card, get_handle_card, search_card


SEARCH_PAGE = """
<ul class="flex flex-wrap -mx-4">
    <li class="lg:w-4/12 px-4 text-center my-4">
        <a href="https://www.fowtcg.com/card/3626">
            <img class="mb-4" src="https://www.fowtcg.com/storage/images/AVL_Pre-Release_Party_F.png">
            <h4 class="font-bold">Guardian Angel, Raphael</h4>
            <p class="mt-2 text-blue-700">AVL Pre-Release Party</p>
        </a>
    </li>
    <li class="lg:w-4/12 px-4 text-center my-4">
        <a href="https://www.fowtcg.com/card/3532">
            <img class="mb-4" src="https://www.fowtcg.com/storage/images/AVL-012.png">
            <h4 class="font-bold">Guardian Angel, Raphael</h4>
            <p class="mt-2 text-blue-700">AVL-012</p>
        </a>
    </li>
    <li class="lg:w-4/12 px-4 text-center my-4">
        <a href="https://www.fowtcg.com/card/3609">
            <img class="mb-4" src="https://www.fowtcg.com/storage/images/AVL-085J.png">
            <h4 class="font-bold">P&#039;Zain, Bearer of the Mind Key</h4>
            <p class="mt-2 text-blue-700">AVL-085</p>
        </a>
    </li>
</ul>
"""

DETAIL_PAGE = """
<div class="relative tab-frame px-2 lg:px-10 py-20 mb-12">
    <img class="mb-12 w-full sm:w-5/12 m-auto" src="https://www.fowtcg.com/storage/images/AVL-085J.png">
    <div class="title-frame text-xl mt-12">P&#039;Zain, Bearer of the Mind Key</div>
    <ul>
        <li class="flex flex-wrap -mx-4 items-center mb-6">
            <div class="balloon1-right w-3/12">Card No.</div>
            <div class="px-4 pl-12 w-9/12 font-bold">AVL-085</div>
"""


def mock_response(text='', content=b'', content_type='text/html'):
    response = MagicMock()
    response.text = text
    response.content = content
    response.headers = {'content-type': content_type}
    return response


def collect(deck_text):
    seen = []
    parse_fow(deck_text, lambda index, name, quantity: seen.append((index, name, quantity)))
    return seen


# --- Unit Tests for Deck Format Parsing ---

class TestFowFormat:
    """Test plain text decklist parsing."""

    def test_sections_are_skipped_and_cards_parsed(self):
        deck_text = """Ruler
1 Lehen, Legendary Explorer
Main Deck
4 Group of Explorers
4x Silmeria, Explorer of Ruins

Magic Stone Deck
3 Light Magic Stone
"""
        assert collect(deck_text) == [
            (1, 'Lehen, Legendary Explorer', 1),
            (2, 'Group of Explorers', 4),
            (3, 'Silmeria, Explorer of Ruins', 4),
            (4, 'Light Magic Stone', 3),
        ]

    def test_crlf(self):
        assert collect('Ruler\r\n1 Divine Custodian, Sol\r\n') == [(1, 'Divine Custodian, Sol', 1)]

    def test_parse_deck_dispatches(self):
        seen = []
        parse_deck('2 Flashfreeze', DeckFormat.FOW, lambda index, name, quantity: seen.append(name))
        assert seen == ['Flashfreeze']

    def test_unrecognized_format_raises(self):
        with pytest.raises(ValueError):
            parse_deck('', 'not_a_real_format', lambda *args: None)

    def test_errors_from_handle_card_are_collected_not_raised(self):
        def failing_handle_card(index, name, quantity):
            raise ValueError('boom')

        parse_fow('1 Flashfreeze\n1 Light Magic Stone', failing_handle_card)


# --- Unit Tests for fowtcg.com lookups (mocked) ---

class TestSearchCard:
    """Test name lookup against the card search results page."""

    def test_prefers_set_printing_over_promo(self):
        with patch.object(fowtcg, 'request_fowtcg', return_value=mock_response(SEARCH_PAGE)):
            card = search_card('Guardian Angel, Raphael')

        assert card == Card(3532, 'https://www.fowtcg.com/storage/images/AVL-012.png', 'Guardian Angel, Raphael', 'AVL-012')

    def test_matches_exact_name_case_insensitive_with_curly_apostrophe(self):
        with patch.object(fowtcg, 'request_fowtcg', return_value=mock_response(SEARCH_PAGE)):
            card = search_card('p’zain, bearer of the mind key')

        assert card.card_id == 3609

    def test_follows_pages_until_exact_match(self):
        first_page = SEARCH_PAGE + '<a href="https://www.fowtcg.com/card_search?free_text=Sol&amp;page=2">'
        second_page = SEARCH_PAGE.replace('Guardian Angel, Raphael', 'Sol')

        with patch.object(fowtcg, 'request_fowtcg', side_effect=[mock_response(first_page), mock_response(second_page)]) as mock_request:
            card = search_card('Sol')

        assert mock_request.call_count == 2
        assert card.card_id == 3532

    def test_missing_card_raises(self):
        with patch.object(fowtcg, 'request_fowtcg', return_value=mock_response(SEARCH_PAGE)):
            with pytest.raises(ValueError):
                search_card('Not A Card')


class TestFindBack:
    """Test detection of a ruler's back face from the neighbouring card id."""

    def test_back_with_same_card_number(self):
        ruler = Card(3608, 'https://www.fowtcg.com/storage/images/AVL-085.png', "All-Seeing One Professor, P'Zain", 'AVL-085')

        with patch.object(fowtcg, 'request_fowtcg', return_value=mock_response(DETAIL_PAGE)) as mock_request:
            back = fowtcg.find_back(ruler)

        mock_request.assert_called_once_with('https://www.fowtcg.com/card/3609')
        assert back.name == "P'Zain, Bearer of the Mind Key"
        assert back.image_url == 'https://www.fowtcg.com/storage/images/AVL-085J.png'

    def test_no_back_for_different_card_number(self):
        card = Card(3608, '', 'Some Resonator', 'AVL-084')

        with patch.object(fowtcg, 'request_fowtcg', return_value=mock_response(DETAIL_PAGE)):
            assert fowtcg.find_back(card) is None

    def test_no_back_when_neighbour_missing(self):
        card = Card(2359, '', 'Water Magic Stone', 'TSD1-019')
        error = fowtcg.requests.HTTPError('500 Server Error')

        with patch.object(fowtcg, 'request_fowtcg', side_effect=error):
            assert fowtcg.find_back(card) is None


class TestFetchImage:
    """Test that non-image responses are rejected."""

    def test_rejects_html(self):
        with patch.object(fowtcg, 'request_fowtcg', return_value=mock_response('<html>', b'<html>', 'text/html')):
            with pytest.raises(ValueError):
                fowtcg.fetch_image('https://www.fowtcg.com/storage/images/missing.png')


# --- Integration Tests for API and Image Fetching ---

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

    def test_fetch_card_with_quantity(self, temp_dirs):
        front_dir, double_sided_dir = temp_dirs

        parse_deck('2 Group of Explorers', DeckFormat.FOW, get_handle_card(front_dir, double_sided_dir))

        files = sorted(os.listdir(front_dir))
        assert files == ['1GroupofExplorers1.png', '1GroupofExplorers2.png']
        assert os.listdir(double_sided_dir) == []
        for f in files:
            Image.open(os.path.join(front_dir, f)).verify()

    def test_fetch_ruler_with_back(self, temp_dirs):
        front_dir, double_sided_dir = temp_dirs

        parse_deck('1 Lehen, Legendary Explorer', DeckFormat.FOW, get_handle_card(front_dir, double_sided_dir))

        assert os.listdir(front_dir) == ['1LehenLegendaryExplorer1.png']
        assert os.listdir(double_sided_dir) == ['1LehenLegendaryExplorer1.png']
        Image.open(os.path.join(double_sided_dir, '1LehenLegendaryExplorer1.png')).verify()
