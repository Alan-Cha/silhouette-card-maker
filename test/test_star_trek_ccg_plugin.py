"""
Tests for the Star Trek CCG plugin.
Tests deck format parsing and image fetching from the Webula mirror of the LackeyCCG Star Trek 2E data.
"""
import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from plugins.star_trek_ccg import api
from plugins.star_trek_ccg.api import get_handle_card, parse_card_data
from plugins.star_trek_ccg.deck_formats import DeckFormat, parse_deck, parse_lackey, parse_trekcc


def collect(parsed_cards):
    def collect_card(index, card_key, quantity):
        parsed_cards.append((index, card_key, quantity))
    return collect_card


# --- Unit Tests for Deck Format Parsing ---

class TestTrekccFormat:
    """Test trekcc.org decklist text export parsing."""

    def test_parse_trekcc(self):
        deck_text = (
            "// https://www.trekcc.org/decklists/?mode=view&deckID=49601\n"
            "\n"
            "Missions\n"
            "Headquarters\n"
            "54\tV\t9\t\t•Earth, Cradle of the Federation\n"
            "Draw Deck (42)\n"
            "Event\n"
            "2\tR\t35\t\t2x Common Ground\n"
            "0\tVP\t22\t\t2x Amanda Rogers\n"
            "55\tV\t27\t\t1x •Beverly Crusher, Principled Physician\r\n"
        )

        parsed_cards = []
        parse_trekcc(deck_text, collect(parsed_cards))

        assert parsed_cards == [
            (1, '54V009', 1),
            (2, '2R035', 2),
            (3, '0VP022', 2),
            (4, '55V027', 1),
        ]


class TestLackeyFormat:
    """Test LackeyCCG deck text export parsing."""

    def test_parse_lackey(self):
        deck_text = (
            "1\tBeverly Crusher Encouraging Commander\n"
            "2\tDelvok\n"
            "Dilemmas:\n"
            "1\tThe Clown: Bitter Medicine\n"
            "Missions:\n"
            "1\tEarth Cradle of the Federation\n"
        )

        parsed_cards = []
        parse_lackey(deck_text, collect(parsed_cards))

        assert parsed_cards == [
            (1, 'Beverly Crusher Encouraging Commander', 1),
            (2, 'Delvok', 2),
            (3, 'The Clown: Bitter Medicine', 1),
            (4, 'Earth Cradle of the Federation', 1),
        ]


class TestParseDeck:
    """Test the format dispatcher."""

    def test_dispatch(self):
        parsed_cards = []
        parse_deck("3\tDelvok", DeckFormat.LACKEY, collect(parsed_cards))
        assert parsed_cards == [(1, 'Delvok', 3)]

    def test_unknown_format(self):
        with pytest.raises(ValueError):
            parse_deck("", "unknown", lambda *args: None)


# --- Unit Tests for Card Data and Image Saving ---

CARD_DATA = (
    "Name\tSet\tImageFile\tRarity\tUnique\tCollectorsInfo\tType\n"
    "Amanda Rogers\tSE\tST2E-EN01121\tR\tN\t1R121\tInterrupt\n"
    "Amanda Rogers (AC)\tAC\tST2E-EN01121ac\tR\tN\t1R121\tInterrupt\n"
    "Gateway Flee in Terror\tOD\tSTVE-EN51007,STVE-EN51007R\tV\tY\t51V007\tMission\r\n"
)


class TestCardData:
    """Test card data lookup."""

    def test_parse_card_data(self):
        cards = parse_card_data(CARD_DATA)

        assert cards['1R121']['ImageFile'] == 'ST2E-EN01121'
        assert cards['Amanda Rogers (AC)']['ImageFile'] == 'ST2E-EN01121ac'
        assert cards['Gateway Flee in Terror']['ImageFile'] == 'STVE-EN51007,STVE-EN51007R'


class TestFetchCard:
    """Test image saving with mocked requests."""

    @pytest.fixture
    def temp_dirs(self):
        front_dir = tempfile.mkdtemp()
        double_sided_dir = tempfile.mkdtemp()
        yield front_dir, double_sided_dir
        shutil.rmtree(front_dir)
        shutil.rmtree(double_sided_dir)

    def mock_get(self, url, **kwargs):
        response = MagicMock()
        response.headers = {'content-type': 'image/jpeg'}
        response.content = b'\xff\xd8\xff\xe0' + url.encode()
        self.requested.append(url)
        return response

    def test_double_sided_mission(self, temp_dirs):
        front_dir, double_sided_dir = temp_dirs
        self.requested = []

        with patch.object(api, 'get_card_data', return_value=parse_card_data(CARD_DATA)), \
             patch.object(api.session, 'get', side_effect=self.mock_get), \
             patch.object(api, 'sleep'):
            parse_deck("51\tV\t7\t\t2x Gateway, Flee in Terror", DeckFormat.TREKCC, get_handle_card(front_dir, double_sided_dir))

        assert sorted(os.listdir(front_dir)) == ['1STVE-EN510071.jpg', '1STVE-EN510072.jpg']
        assert sorted(os.listdir(double_sided_dir)) == ['1STVE-EN510071.jpg', '1STVE-EN510072.jpg']
        with open(os.path.join(double_sided_dir, '1STVE-EN510071.jpg'), 'rb') as f:
            assert f.read().endswith(b'STVE-EN51007R.jpg')

    def test_non_image_response(self, temp_dirs, capsys):
        front_dir, double_sided_dir = temp_dirs
        response = MagicMock()
        response.headers = {'content-type': 'text/html'}

        with patch.object(api, 'get_card_data', return_value=parse_card_data(CARD_DATA)), \
             patch.object(api.session, 'get', return_value=response), \
             patch.object(api, 'sleep'):
            parse_deck("1\tAmanda Rogers", DeckFormat.LACKEY, get_handle_card(front_dir, double_sided_dir))

        assert os.listdir(front_dir) == []
        assert 'not an image' in capsys.readouterr().out

    def test_unknown_card(self, temp_dirs, capsys):
        front_dir, double_sided_dir = temp_dirs

        with patch.object(api, 'get_card_data', return_value=parse_card_data(CARD_DATA)):
            parse_deck("1\tNot A Card", DeckFormat.LACKEY, get_handle_card(front_dir, double_sided_dir))

        assert os.listdir(front_dir) == []
        assert 'Card "Not A Card" not found' in capsys.readouterr().out


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

    def test_fetch_trekcc_and_lackey(self, temp_dirs):
        front_dir, double_sided_dir = temp_dirs
        handle_card = get_handle_card(front_dir, double_sided_dir)

        parse_deck("55\tV\t27\t\t1x •Beverly Crusher, Principled Physician", DeckFormat.TREKCC, handle_card)
        parse_deck("1\tGateway Flee in Terror", DeckFormat.LACKEY, handle_card)

        assert sorted(os.listdir(front_dir)) == ['1STVE-EN510071.jpg', '1STVE-EN550271.jpg']
        assert os.listdir(double_sided_dir) == ['1STVE-EN510071.jpg']
        for directory in (front_dir, double_sided_dir):
            for f in os.listdir(directory):
                with Image.open(os.path.join(directory, f)) as img:
                    img.verify()
