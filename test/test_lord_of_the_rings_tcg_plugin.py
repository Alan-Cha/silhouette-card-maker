"""
Tests for the Lord of the Rings TCG plugin.
Tests deck format parsing and image fetching from the Players Council wiki.
"""
import os
import shutil
import tempfile
import pytest

from PIL import Image

from plugins.lord_of_the_rings_tcg import deck_formats, lotrtcgpc
from plugins.lord_of_the_rings_tcg.deck_formats import (
    DeckFormat,
    parse_deck,
    parse_gemp_id,
    parse_gemp_url,
)
from plugins.lord_of_the_rings_tcg.lotrtcgpc import get_card_art_url, get_handle_card


PC_CARDS_JS = """var PCCards = {
	// '101_1': 'https://i.lotrtcgpc.net/sets/fotr_starters/playtest/101_1.jpg',
	'55_8': 'https://i.lotrtcgpc.net/errata/LOTR-EN05E008.1_card.jpg',
	'101_1':  'https://i.lotrtcgpc.net/sets/vset1/V1_001.jpg',
	'101_1'  : 'https://i.lotrtcgpc.net/sets/vset1/LOTR-ENV1E001.1_card.jpg',
}
"""


@pytest.fixture
def pc_cards(monkeypatch):
    """Serve a real-shaped PC_Cards.js snippet instead of fetching it."""
    class FakeResponse:
        text = PC_CARDS_JS

    lotrtcgpc.load_pc_card_images.cache_clear()
    monkeypatch.setattr(lotrtcgpc, 'request_lotrtcgpc', lambda url: FakeResponse())
    yield
    lotrtcgpc.load_pc_card_images.cache_clear()


def collect_cards(parse, deck_text):
    parsed_cards = []
    def collect_card(index, image_url, quantity):
        parsed_cards.append({
            'index': index,
            'image_url': image_url,
            'quantity': quantity
        })

    parse(deck_text, collect_card)
    return parsed_cards


# --- Unit Tests for Image URLs ---

@pytest.mark.usefixtures('pc_cards')
class TestCardArtUrl:
    """Test Gemp blueprint id to image URL mapping."""

    def test_load_pc_card_images(self):
        assert lotrtcgpc.load_pc_card_images() == {
            '55_8': 'https://i.lotrtcgpc.net/errata/LOTR-EN05E008.1_card.jpg',
            '101_1': 'https://i.lotrtcgpc.net/sets/vset1/LOTR-ENV1E001.1_card.jpg',
        }

    def test_decipher_set(self):
        assert get_card_art_url('1_79') == 'https://wiki.lotrtcgpc.net/images/LOTR-EN01S079.0_card.jpg'

    def test_double_digit_set(self):
        assert get_card_art_url('19_1') == 'https://wiki.lotrtcgpc.net/images/LOTR-EN19S001.0_card.jpg'

    def test_errata_set(self):
        assert get_card_art_url('55_8') == 'https://i.lotrtcgpc.net/errata/LOTR-EN05E008.1_card.jpg'
        assert get_card_art_url('51_40') == 'https://wiki.lotrtcgpc.net/images/LOTR-EN01E040.1_card.jpg'
        assert get_card_art_url('71_3') == 'https://wiki.lotrtcgpc.net/images/LOTR-EN01E003.1_card.jpg'

    def test_players_council_set(self):
        assert get_card_art_url('101_1') == 'https://i.lotrtcgpc.net/sets/vset1/LOTR-ENV1E001.1_card.jpg'
        assert get_card_art_url('101_2') == 'https://wiki.lotrtcgpc.net/images/LOTR-ENV1S002.0_card.jpg'

    def test_foil_and_tengwar_suffixes(self):
        assert get_card_art_url('1_2*') == 'https://wiki.lotrtcgpc.net/images/LOTR-EN01S002.0_card.jpg'
        assert get_card_art_url('1_2T') == 'https://wiki.lotrtcgpc.net/images/LOTR-EN01S002.0_card.jpg'


# --- Unit Tests for Deck Format Parsing ---

@pytest.mark.usefixtures('pc_cards')
class TestGempIdFormat:
    """Test Gemp blueprint id format parsing."""

    def test_parse_gemp_id(self):
        deck_text = """Ring-bearer
1_290
1_2
Draw deck
2x 2_6
3 1_51*
1x 101_1"""

        parsed_cards = collect_cards(parse_gemp_id, deck_text)

        assert len(parsed_cards) == 5
        assert parsed_cards[0]['image_url'].endswith('LOTR-EN01S290.0_card.jpg')
        assert parsed_cards[0]['quantity'] == 1
        assert parsed_cards[2]['image_url'].endswith('LOTR-EN02S006.0_card.jpg')
        assert parsed_cards[2]['quantity'] == 2
        assert parsed_cards[3]['quantity'] == 3
        assert parsed_cards[4]['image_url'].endswith('LOTR-ENV1E001.1_card.jpg')


class TestGempUrlFormat:
    """Test Gemp deck HTML page parsing."""

    DECK_HTML = (
        '<html><body><div><h1>aldlsgvzxc</h1><h2>Format: limited_fotr</h2><h2>Author: Wingfoot81</h2>'
        '<b>Ring-bearer:</b> <span class="tooltip">Frodo, Son of Drogo<span><img class="ttimage" src="https://wiki.lotrtcgpc.net/images/LOTR-EN01S290.0_card.jpg" ></span></span><br/>'
        '<b>Ring:</b> <span class="tooltip">The One Ring, The Ruling Ring<span><img class="ttimage" src="https://wiki.lotrtcgpc.net/images/LOTR-EN01S002.0_card.jpg" ></span></span><br/><br/>'
        '<b>Adventure deck:</b><br/>'
        '<span class="tooltip">The Prancing Pony<span><img class="ttimage" src="https://wiki.lotrtcgpc.net/images/LOTR-EN01S324.0_card.jpg" ></span></span><br/><br/>'
        '<b>Free Peoples Draw Deck:</b><br/>'
        '2x <span class="tooltip">Fror, Gimli&#39;s Kinsman<span><img class="ttimage" src="https://wiki.lotrtcgpc.net/images/LOTR-EN02S006.0_card.jpg" ></span></span><br/>'
        '1x <span class="tooltip">Speak &quot;Friend&quot; and Enter<span><img class="ttimage" src="https://wiki.lotrtcgpc.net/images/LOTR-EN02S026.0_card.jpg" ></span></span><br/>'
        '</div></body></html>'
    )

    def test_parse_gemp_url(self, monkeypatch):
        requested = []
        def fake_fetch_deck_html(url):
            requested.append(url)
            return self.DECK_HTML

        monkeypatch.setattr(deck_formats, 'fetch_deck_html', fake_fetch_deck_html)

        deck_url = 'https://play.lotrtcgpc.net/gemp-lotr-server/tournament/limited_fotr1790739760824/deck/Wingfoot81/html'
        parsed_cards = collect_cards(parse_gemp_url, f'{deck_url}\n')

        assert requested == [deck_url]
        assert len(parsed_cards) == 5
        assert parsed_cards[0]['image_url'].endswith('LOTR-EN01S290.0_card.jpg')
        assert parsed_cards[1]['image_url'].endswith('LOTR-EN01S002.0_card.jpg')
        assert parsed_cards[2]['quantity'] == 1
        assert parsed_cards[3]['quantity'] == 2
        assert parsed_cards[4]['image_url'].endswith('LOTR-EN02S026.0_card.jpg')

    def test_parse_gemp_url_rejects_non_url(self):
        with pytest.raises(ValueError):
            collect_cards(parse_gemp_url, '1_79')


# --- Integration Tests for Image Fetching ---

@pytest.mark.integration
class TestFullFetchWorkflow:
    """Integration tests for the complete card fetching workflow."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for test output."""
        front_dir = tempfile.mkdtemp()
        yield front_dir
        shutil.rmtree(front_dir)

    def test_fetch_with_quantity(self, temp_dirs):
        """Test fetching a card with quantity > 1."""
        front_dir = temp_dirs

        parse_deck('2x 1_79', DeckFormat.GEMP_ID, get_handle_card(front_dir))

        files = sorted(os.listdir(front_dir))
        assert files == ['1LOTR-EN01S079.01.jpg', '1LOTR-EN01S079.02.jpg']

        for f in files:
            with Image.open(os.path.join(front_dir, f)) as image:
                image.verify()

    def test_fetch_errata_card(self, temp_dirs):
        """Test fetching a Players Council errata card from Gemp's image overrides."""
        front_dir = temp_dirs

        parse_deck('55_8', DeckFormat.GEMP_ID, get_handle_card(front_dir))

        files = os.listdir(front_dir)
        assert files == ['1LOTR-EN05E008.11.jpg']

        with Image.open(os.path.join(front_dir, files[0])) as image:
            image.verify()

    def test_missing_card_is_skipped(self, temp_dirs):
        """Test that a card without a wiki image does not write a file."""
        front_dir = temp_dirs

        parse_deck('1_999', DeckFormat.GEMP_ID, get_handle_card(front_dir))

        assert os.listdir(front_dir) == []
