"""
Tests for the Sorcery: Contested Realm plugin.
Tests API integration with sorcerytcg.com (formerly curiosa.io).
"""
import os
import shutil
import tempfile
import pytest
from PIL import Image

from plugins.sorcery_contested_realm import curiosa
from plugins.sorcery_contested_realm.curiosa import get_curiosa_decklist, get_handle_card, save_atlas_back, SORCERY_API_BASE, DECK_ENDPOINT
from plugins.sorcery_contested_realm.deck_formats import DeckFormat, parse_deck


# --- Unit Tests ---

class TestDeckFormatEnum:
    """Test the DeckFormat enum values."""

    def test_curiosa_url_format_value(self):
        """Test that the CURIOSA_URL format has the expected value."""
        assert DeckFormat.CURIOSA_URL.value == 'curiosa_url'


class TestCuriosaurlFormat:
    """Test Curiosa deck URL format parsing."""

    def test_share_url_pattern_matches(self):
        """Test that valid Curiosa deck URLs are detected."""
        import re
        pattern = re.compile(r'https://curiosa\.io/decks/(\w+)')

        assert pattern.match("https://curiosa.io/decks/cme5x329q00k9jo04ouuycsek")
        assert pattern.match("https://curiosa.io/decks/abc123")

    def test_share_url_pattern_rejects_invalid(self):
        """Test that invalid lines are rejected."""
        import re
        pattern = re.compile(r'https://curiosa\.io/decks/(\w+)')

        assert not pattern.match("")
        assert not pattern.match("cme5x329q00k9jo04ouuycsek")  # bare ID, no URL
        assert not pattern.match("https://example.com/decks/cme5x329q00k9jo04ouuycsek")

    def test_share_url_extracts_deck_id(self):
        """Test that the deck ID is correctly extracted from a URL."""
        import re
        pattern = re.compile(r'https://curiosa\.io/decks/(\w+)')

        match = pattern.match("https://curiosa.io/decks/cme5x329q00k9jo04ouuycsek")
        assert match is not None
        assert match.group(1) == "cme5x329q00k9jo04ouuycsek"


class TestAtlasBack:
    """Test that Sites get the atlas card back in the double-sided directory."""

    @pytest.fixture
    def dirs(self):
        """Create temporary front, double-sided, and source directories."""
        root = tempfile.mkdtemp()
        front_dir = os.path.join(root, 'front')
        ds_dir = os.path.join(root, 'double_sided')
        os.makedirs(front_dir)
        os.makedirs(ds_dir)
        atlas_back = os.path.join(root, 'atlas_back.png')
        Image.new('RGB', (70, 50), 'blue').save(atlas_back)
        yield front_dir, ds_dir, atlas_back
        shutil.rmtree(root)

    @pytest.fixture
    def fake_request(self, monkeypatch):
        """Serve a small portrait PNG instead of downloading card art."""
        card_path = os.path.join(tempfile.mkdtemp(), 'card.png')
        Image.new('RGB', (50, 70), 'red').save(card_path)
        with open(card_path, 'rb') as f:
            content = f.read()

        class FakeResponse:
            pass

        response = FakeResponse()
        response.content = content
        monkeypatch.setattr(curiosa, 'request_curiosa', lambda url: response)
        yield
        shutil.rmtree(os.path.dirname(card_path))

    def test_landscape_atlas_back_is_rotated_to_portrait(self, dirs):
        """Test that a landscape atlas back is saved in portrait orientation."""
        _, ds_dir, atlas_back = dirs
        output = os.path.join(ds_dir, 'site.png')

        save_atlas_back(atlas_back, output)

        with Image.open(output) as image:
            assert image.size == (50, 70)

    def test_site_copies_get_atlas_back(self, dirs, fake_request):
        """Test that each copy of a Site gets a double-sided back with the same file name."""
        front_dir, ds_dir, atlas_back = dirs
        handle_card = get_handle_card(front_dir, ds_dir, atlas_back)

        handle_card(1, 'Arid Desert', 'https://example.com/site.png', 2, True)

        assert sorted(os.listdir(front_dir)) == ['1AridDesert1.png', '1AridDesert2.png']
        assert sorted(os.listdir(ds_dir)) == sorted(os.listdir(front_dir))

    def test_spell_gets_no_atlas_back(self, dirs, fake_request):
        """Test that a non-Site card gets no double-sided back."""
        front_dir, ds_dir, atlas_back = dirs
        handle_card = get_handle_card(front_dir, ds_dir, atlas_back)

        handle_card(1, 'Fireball', 'https://example.com/spell.png', 1, False)

        assert os.listdir(front_dir) == ['1Fireball1.png']
        assert os.listdir(ds_dir) == []

    def test_site_without_atlas_back_option(self, dirs, fake_request):
        """Test that Sites get no double-sided back when no atlas back is given."""
        front_dir, ds_dir, _ = dirs
        handle_card = get_handle_card(front_dir, ds_dir)

        handle_card(1, 'Arid Desert', 'https://example.com/site.png', 1, True)

        assert os.listdir(ds_dir) == []


# --- Integration Tests ---

@pytest.mark.integration
class TestCuriosaTRPCAPI:
    """Test Curiosa TRPC API requests."""

    def test_curiosa_api_availability(self):
        """Test that the sorcerytcg.com TRPC API server is reachable."""
        # An unknown deck ID returns HTTP 404, which the plugin reports as an empty decklist
        decklist = get_curiosa_decklist('invalid-deck-id-for-availability-test')
        assert decklist == []

    def test_curiosa_api_base_url(self):
        """Test that the sorcerytcg.com API base URL is configured correctly."""
        assert SORCERY_API_BASE == 'https://sorcerytcg.com/api/trpc/'

    def test_curiosa_deck_endpoint(self):
        """Test that the expected deck endpoint is configured."""
        assert DECK_ENDPOINT == 'deck.get'


@pytest.mark.integration
class TestFullFetchWorkflow:
    """Integration tests for the complete card fetching workflow."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for test output."""
        front_dir = tempfile.mkdtemp()
        yield front_dir
        shutil.rmtree(front_dir)

    def test_fetch_deck_from_curiosa(self, temp_dirs):
        """Test fetching cards from a Curiosa deck URL."""
        front_dir = temp_dirs

        deck_url = "https://curiosa.io/decks/cme5x329q00k9jo04ouuycsek"

        handle_card = get_handle_card(front_dir)
        parse_deck(deck_url, DeckFormat.CURIOSA_URL, handle_card)

        files = os.listdir(front_dir)
        assert len(files) >= 1

        for f in files:
            file_path = os.path.join(front_dir, f)
            assert os.path.getsize(file_path) > 0

    def test_fetch_deck_from_sorcerytcg(self, temp_dirs):
        """Test fetching cards from a sorcerytcg.com deck URL."""
        front_dir = temp_dirs

        deck_url = "https://sorcerytcg.com/decks/cme5x329q00k9jo04ouuycsek"

        handle_card = get_handle_card(front_dir)
        parse_deck(deck_url, DeckFormat.CURIOSA_URL, handle_card)

        assert len(os.listdir(front_dir)) >= 1
