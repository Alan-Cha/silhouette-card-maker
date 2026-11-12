"""
Tests for the UniVersus plugin.
Tests deck format parsing and image fetching from universus.cards.
"""
import io
import json
import os
import shutil
import tempfile
import pytest
from PIL import Image

from plugins.universus.deck_formats import (
    DeckFormat,
    parse_deck,
    parse_universus_json,
    parse_universus_text,
    parse_universus_url,
    extract_universus_cards,
)
from plugins.universus import universus
from plugins.universus.universus import get_card_id, get_card_images, get_universus_deck, get_handle_card


DECK_ID = 'e4c57177-8a10-40e6-9786-0cbf35268bd9'

# Trimmed deck JSON as served by https://universus.cards/deck/{id}
DECK_JSON = json.dumps({
    '_id': DECK_ID,
    'name': 'Ives Kailub (Reiner Braun)',
    'format': 'Standard',
    'cards': [[10405, 1, 1], [10943, 1, 0], [10897, 3, 0], [11927, 0, 1]],
    'maybeboard': [],
    'startingCharacter': 10943,
})

# Trimmed "Display As: Decklist" text from https://universus.cards/deck/{id}?display=Decklist
DECK_TEXT = """
# Starting Character

1 Reiner Braun | Attack on Titan: Battle for Humanity

# Mainboard

## Action

1 Genkai's Guidance | Yu Yu Hakusho: Dark Tournament
3 Chomp | Attack on Titan: Battle for Humanity

# Sideboard

## Action

1 Genkai's Guidance | Yu Yu Hakusho: Dark Tournament
1 Filled with Doubt | Attack on Titan: Apocalypse

# Maybeboard

1 Showdown | League of Villains
"""

TEXT_CARD_IDS = {
    'Reiner Braun': 10943,
    "Genkai's Guidance": 10405,
    'Chomp': 10897,
    'Filled with Doubt': 11927,
}


def collect(parsed_cards):
    def collect_card(index, card_id, quantity):
        parsed_cards.append({'index': index, 'card_id': card_id, 'quantity': quantity})
    return collect_card


# --- Unit Tests for Deck Format Parsing ---

class TestUniversusJsonFormat:
    """Test universus.cards deck JSON parsing."""

    def test_parse_universus_json(self):
        parsed_cards = []
        parse_universus_json(DECK_JSON, collect(parsed_cards))

        assert [(c['card_id'], c['quantity']) for c in parsed_cards] == [
            (10943, 1),  # starting character first
            (10405, 2),  # mainboard + sideboard
            (10897, 3),
            (11927, 1),  # sideboard only
        ]
        assert [c['index'] for c in parsed_cards] == [1, 2, 3, 4]

    def test_starting_character_added_when_missing(self):
        deck = {'cards': [[10897, 3, 0]], 'startingCharacter': 10943}
        assert extract_universus_cards(deck) == [(10943, 1), (10897, 3)]

    def test_ignore_sideboard(self):
        parsed_cards = []
        parse_deck(DECK_JSON, DeckFormat.UNIVERSUS_JSON, collect(parsed_cards), ignore_sideboard = True)

        assert [(c['card_id'], c['quantity']) for c in parsed_cards] == [
            (10943, 1),
            (10405, 1),
            (10897, 3),
        ]

    def test_parse_deck_dispatch(self):
        parsed_cards = []
        parse_deck(DECK_JSON, DeckFormat.UNIVERSUS_JSON, collect(parsed_cards))
        assert len(parsed_cards) == 4


class TestUniversusUrlFormat:
    """Test universus.cards deck URL parsing without network access."""

    def test_parse_universus_url(self, monkeypatch):
        requested = []
        def fake_get_deck(deck_id):
            requested.append(deck_id)
            return json.loads(DECK_JSON)
        monkeypatch.setattr('plugins.universus.deck_formats.get_universus_deck', fake_get_deck)

        parsed_cards = []
        parse_universus_url(f'https://universus.cards/deck/{DECK_ID}\nnot a url', collect(parsed_cards))

        assert requested == [DECK_ID]
        assert parsed_cards[0]['card_id'] == 10943
        assert len(parsed_cards) == 4


class TestUniversusTextFormat:
    """Test universus.cards decklist text parsing without network access."""

    @pytest.fixture(autouse = True)
    def fake_card_ids(self, monkeypatch):
        monkeypatch.setattr('plugins.universus.deck_formats.get_card_id', lambda name, set_name: TEXT_CARD_IDS[name])

    def test_parse_universus_text(self):
        parsed_cards = []
        parse_universus_text(DECK_TEXT, collect(parsed_cards))

        assert [(c['card_id'], c['quantity']) for c in parsed_cards] == [
            (10943, 1),  # starting character first
            (10405, 2),  # mainboard + sideboard
            (10897, 3),
            (11927, 1),  # sideboard only, maybeboard skipped
        ]

    def test_ignore_sideboard(self):
        parsed_cards = []
        parse_deck(DECK_TEXT, DeckFormat.UNIVERSUS_TEXT, collect(parsed_cards), ignore_sideboard = True)

        assert [(c['card_id'], c['quantity']) for c in parsed_cards] == [(10943, 1), (10405, 1), (10897, 3)]


def jpg_bytes(width):
    buffer = io.BytesIO()
    Image.new('RGB', (width, width * 7 // 5)).save(buffer, 'JPEG')
    return buffer.getvalue()


class TestLargestImage:
    """Test choosing between universus.cards and uvsultra.online images without network access."""

    URL = 'https://universus.cards/cards/aot01/017.jpg'

    def fake_images(self, monkeypatch, images):
        requested = []
        def fake_request_image(url):
            requested.append(url)
            if url not in images:
                raise ValueError('404')
            return images[url]
        monkeypatch.setattr(universus, 'request_image', fake_request_image)
        return requested

    def test_prefers_larger_uvsultra_image(self, monkeypatch):
        large = jpg_bytes(744)
        requested = self.fake_images(monkeypatch, {self.URL: jpg_bytes(358), 'https://uvsultra.online/images/extensions/aot01/017.jpg': large})
        assert universus.request_largest_image(self.URL) == large
        assert requested[1] == 'https://uvsultra.online/images/extensions/aot01/017.jpg'

    def test_keeps_larger_universus_image(self, monkeypatch):
        small = jpg_bytes(358)
        self.fake_images(monkeypatch, {self.URL: small, 'https://uvsultra.online/images/extensions/aot01/017.jpg': jpg_bytes(300)})
        assert universus.request_largest_image(self.URL) == small

    def test_falls_back_when_uvsultra_missing(self, monkeypatch):
        small = jpg_bytes(358)
        self.fake_images(monkeypatch, {self.URL: small})
        assert universus.request_largest_image(self.URL) == small


# --- Integration Tests for API and Image Fetching ---

@pytest.mark.integration
class TestUniversusAPI:
    """Test universus.cards requests."""

    def test_get_deck(self):
        deck = get_universus_deck(DECK_ID)
        assert deck['startingCharacter'] == 10943
        assert len(deck['cards']) > 0

    def test_get_card_images_double_sided(self):
        name, front, back = get_card_images(10943)
        assert name == 'Reiner Braun'
        assert front.endswith('/cards/aot01/017.jpg')
        assert back.endswith('/cards/aot01/017B.jpg')

    def test_get_card_id(self):
        assert get_card_id("Genkai's Guidance", 'Yu Yu Hakusho: Dark Tournament') == 10405
        # Name search matches substrings; only the exact name counts
        assert get_card_id('Chomp', 'Attack on Titan: Battle for Humanity') == 10897

    def test_uvsultra_image_is_larger(self):
        content = universus.request_largest_image('https://universus.cards/cards/aot01/017.jpg')
        assert universus.image_width(content) > 358


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

    def test_fetch_double_sided_with_quantity(self, temp_dirs):
        front_dir, double_sided_dir = temp_dirs

        deck_text = json.dumps({'cards': [[10405, 1, 1]], 'startingCharacter': 10943})
        parse_deck(deck_text, DeckFormat.UNIVERSUS_JSON, get_handle_card(front_dir, double_sided_dir))

        assert sorted(os.listdir(front_dir)) == ['1ReinerBraun1.jpg', '2GenkaisGuidance1.jpg', '2GenkaisGuidance2.jpg']
        assert os.listdir(double_sided_dir) == ['1ReinerBraun1.jpg']

        for directory in temp_dirs:
            for f in os.listdir(directory):
                with Image.open(os.path.join(directory, f)) as img:
                    img.verify()
