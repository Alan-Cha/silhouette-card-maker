"""
Tests for the Duel Masters plugin.
Tests deck format parsing and image fetching.
"""
import os
import shutil
import tempfile
from io import BytesIO
from unittest.mock import MagicMock

import pytest
from PIL import Image

from plugins.duel_masters import takaratomy
from plugins.duel_masters.deck_formats import (
    DeckFormat,
    parse_deck,
    parse_official,
    parse_id,
)
from plugins.duel_masters.takaratomy import get_handle_card, normalize_name


def collect(parsed_cards):
    def collect_card(index, card_id, name, quantity):
        parsed_cards.append({
            'index': index,
            'card_id': card_id,
            'name': name,
            'quantity': quantity,
        })
    return collect_card


# --- Unit Tests for Deck Format Parsing ---

class TestOfficialFormat:
    """Test the official tournament coverage format."""

    def test_parse_official(self):
        deck_text = """おんそく
全国大会2025 日本一決定戦
20　クリーチャー
4	《Disコットン＆Disケラサス》
2	《切札勝太&カツキング ー熱血の物語ー》
6　ツインパクト
4	《支配の精霊ペルフェクト / ギャラクシー・チャージャー》"""

        parsed_cards = []
        parse_official(deck_text, collect(parsed_cards))

        assert len(parsed_cards) == 3
        assert parsed_cards[0] == {'index': 1, 'card_id': '', 'name': 'Disコットン＆Disケラサス', 'quantity': 4}
        assert parsed_cards[1]['name'] == '切札勝太&カツキング ー熱血の物語ー'
        assert parsed_cards[2]['name'] == '支配の精霊ペルフェクト / ギャラクシー・チャージャー'
        assert parsed_cards[2]['quantity'] == 4

    def test_section_headings_skipped(self, capsys):
        parsed_cards = []
        parse_official('20　クリーチャー\n14　呪文その他', collect(parsed_cards))

        assert parsed_cards == []
        assert 'Skipping: "20　クリーチャー"' in capsys.readouterr().out


class TestIdFormat:
    """Test the card ID format."""

    def test_parse_id(self):
        deck_text = """4 dm26rp3-001
2 dm24bd5-006
1 dm37-030
3 dm26rp2-T008"""

        parsed_cards = []
        parse_id(deck_text, collect(parsed_cards))

        assert len(parsed_cards) == 4
        assert parsed_cards[0] == {'index': 1, 'card_id': 'dm26rp3-001', 'name': '', 'quantity': 4}
        assert parsed_cards[2]['card_id'] == 'dm37-030'
        assert parsed_cards[3]['card_id'] == 'dm26rp2-T008'


class TestParseDeck:
    """Test the deck format dispatcher."""

    def test_unknown_format(self):
        with pytest.raises(ValueError):
            parse_deck('4 dm26rp3-001', 'unknown', lambda *args: None)

    def test_errors_are_collected(self, capsys):
        def failing_card(index, card_id, name, quantity):
            raise ValueError('boom')

        parse_deck('4 dm26rp3-001', DeckFormat.ID, failing_card)

        out = capsys.readouterr().out
        assert 'Error: boom' in out
        assert 'Errors:' in out


# --- Unit Tests for Card Lookup ---

SEARCH_HTML = """<ul class="cardList01 clearfix">
<li><a href='/card/detail/?id=dm26rp3-002' data-href='/card/detail/?id=dm26rp3-002'><img class='cardImage' data-href='/card/detail/?id=dm26rp3-002' src='/wp-content/card/cardthumb/dm26rp3-002.jpg' alt=' ' loading='lazy'/></a></li>
<li><a href='/card/detail/?id=dm24bd5-006' data-href='/card/detail/?id=dm24bd5-006'><img class='cardImage' data-href='/card/detail/?id=dm24bd5-006' src='/wp-content/card/cardthumb/dm24bd5-006.jpg' alt=' ' loading='lazy'/></a></li>
</ul>"""

DETAIL_HTML = {
    'dm26rp3-002': '<div class="cardarea"><img src="/wp-content/card/cardimage/dm26rp3-002.jpg" alt="宇宙妖精エリンギ・改"></div>',
    'dm24bd5-006': '<div class="cardarea"><img src="/wp-content/card/cardimage/dm24bd5-006.jpg" alt="宇宙妖精エリンギ"></div>',
    'dm37-030': '<div class="cardarea"><img src="/wp-content/card/cardimage/dm37-030a.jpg" alt="時空の喧嘩屋キル"><img src="/wp-content/card/cardimage/dm37-030b.jpg" alt="巨人の覚醒者セツダン"></div>',
}


def png_bytes():
    buffer = BytesIO()
    Image.new('RGB', (10, 14)).save(buffer, format='PNG')
    return buffer.getvalue()


@pytest.fixture
def mock_site(monkeypatch):
    image = png_bytes()
    requested_images = []

    def fake_request(method, url, **kwargs):
        response = MagicMock()
        if url == takaratomy.SEARCH_URL:
            response.text = SEARCH_HTML
        elif url == takaratomy.DETAIL_URL:
            response.text = DETAIL_HTML[kwargs['params']['id']]
        else:
            requested_images.append(url)
            response.headers = {'content-type': 'image/jpeg'}
            response.content = image
        return response

    monkeypatch.setattr(takaratomy, 'request_takaratomy', fake_request)
    return requested_images


@pytest.fixture
def temp_dirs():
    front_dir = tempfile.mkdtemp()
    double_sided_dir = tempfile.mkdtemp()
    yield front_dir, double_sided_dir
    shutil.rmtree(front_dir)
    shutil.rmtree(double_sided_dir)


class TestCardLookup:
    """Test card lookup against mocked official site responses."""

    def test_normalize_name(self):
        assert normalize_name('Disコットン＆Disケラサス') == normalize_name('Disコットン&Disケラサス')

    def test_find_card_exact_name(self, mock_site):
        card_id, faces = takaratomy.find_card('宇宙妖精エリンギ')

        assert card_id == 'dm24bd5-006'
        assert faces == [('https://dm.takaratomy.co.jp/wp-content/card/cardimage/dm24bd5-006.jpg', '宇宙妖精エリンギ')]

    def test_find_card_missing(self, mock_site):
        with pytest.raises(ValueError):
            takaratomy.find_card('存在しないカード')

    def test_fetch_by_name(self, mock_site, temp_dirs):
        front_dir, double_sided_dir = temp_dirs

        get_handle_card(front_dir, double_sided_dir)(3, '', '宇宙妖精エリンギ', 2)

        assert sorted(os.listdir(front_dir)) == ['3dm24bd5-0061.png', '3dm24bd5-0062.png']
        assert os.listdir(double_sided_dir) == []

    def test_fetch_double_sided(self, mock_site, temp_dirs):
        front_dir, double_sided_dir = temp_dirs

        get_handle_card(front_dir, double_sided_dir)(1, 'dm37-030', '', 1)

        assert os.listdir(front_dir) == ['1dm37-0301.png']
        assert os.listdir(double_sided_dir) == ['1dm37-0301.png']
        assert mock_site == [
            'https://dm.takaratomy.co.jp/wp-content/card/cardimage/dm37-030a.jpg',
            'https://dm.takaratomy.co.jp/wp-content/card/cardimage/dm37-030b.jpg',
        ]

    def test_rejects_non_image(self, monkeypatch):
        response = MagicMock()
        response.headers = {'content-type': 'text/html; charset=UTF-8'}
        monkeypatch.setattr(takaratomy, 'request_takaratomy', lambda method, url, **kwargs: response)

        with pytest.raises(ValueError):
            takaratomy.download_image('https://dm.takaratomy.co.jp/wp-content/card/cardimage/missing.jpg')


# --- Integration Tests for API and Image Fetching ---

@pytest.mark.integration
class TestFullFetchWorkflow:
    """Integration tests for the complete card fetching workflow."""

    def test_fetch_double_sided_by_id(self, temp_dirs):
        front_dir, double_sided_dir = temp_dirs

        parse_deck('1 dm37-030', DeckFormat.ID, get_handle_card(front_dir, double_sided_dir))

        assert os.listdir(front_dir) == ['1dm37-0301.jpg']
        assert os.listdir(double_sided_dir) == ['1dm37-0301.jpg']
        for directory in (front_dir, double_sided_dir):
            with Image.open(os.path.join(directory, '1dm37-0301.jpg')) as img:
                img.verify()

    def test_fetch_by_name(self, temp_dirs):
        front_dir, double_sided_dir = temp_dirs

        parse_deck('2\t《宇宙妖精エリンギ》', DeckFormat.OFFICIAL, get_handle_card(front_dir, double_sided_dir))

        files = sorted(os.listdir(front_dir))
        assert len(files) == 2
        for f in files:
            with Image.open(os.path.join(front_dir, f)) as img:
                img.verify()
