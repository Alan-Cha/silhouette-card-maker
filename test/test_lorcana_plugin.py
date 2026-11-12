"""
Tests for the Lorcana plugin.
Tests deck format parsing and image fetching from Lorcast.
"""

import os
import shutil
import tempfile
import pytest

from plugins.lorcana.deck_formats import (
    CardVariant,
    DeckFormat,
    parse_deck,
    parse_dreamborn_list,
)
from plugins.lorcana.common import remove_nonalphanumeric
from plugins.lorcana.lorcast import (
    request_lorcast,
    get_handle_card as lorcast_get_handle_card,
    format_lorcast_query,
)
from plugins.lorcana.dreamborn import (
    format_dreamborn_name,
    format_dreamborn_title,
    request_dreamborn,
    get_handle_card as dreamborn_get_handle_card,
)

# --- Unit Tests for Deck Format Parsing ---


class TestDreambornFormat:
    """Test Dreamborn format parsing."""

    def test_parse_dreamborn_basic(self):
        """Test parsing basic Dreamborn format."""
        deck_text = """1 Elsa, Spirit of Winter
4 Magic Broom, Illuminary Keeper
2 Diablo - Obedient Raven"""

        parsed_cards = []

        def collect_card(index, name, variant, quantity):
            parsed_cards.append(
                {
                    "index": index,
                    "name": name,
                    "variant": variant,
                    "quantity": quantity,
                }
            )

        parse_dreamborn_list(deck_text, collect_card)

        assert len(parsed_cards) == 3
        assert parsed_cards[0]["name"] == "Elsa, Spirit of Winter"
        assert parsed_cards[0]["variant"] is None
        assert parsed_cards[0]["quantity"] == 1
        assert parsed_cards[1]["name"] == "Magic Broom, Illuminary Keeper"
        assert parsed_cards[1]["quantity"] == 4

    def test_parse_dreamborn_with_enchanted(self):
        """Test parsing Dreamborn format with enchanted marker."""
        deck_text = """1 Anna - True-Hearted *E*
2 Elsa, Spirit of Winter"""

        parsed_cards = []

        def collect_card(index, name, variant, quantity):
            parsed_cards.append(
                {
                    "index": index,
                    "name": name,
                    "variant": variant,
                    "quantity": quantity,
                }
            )

        parse_dreamborn_list(deck_text, collect_card)

        assert len(parsed_cards) == 2
        assert parsed_cards[0]["name"] == "Anna - True-Hearted"
        assert parsed_cards[0]["variant"] == CardVariant.ENCHANTED
        assert parsed_cards[1]["variant"] is None

    def test_parse_dreamborn_with_epic_and_iconic(self):
        """Test parsing Dreamborn format with epic and iconic markers."""
        deck_text = """1 Max Goof - Rockin' Teen *EPIC*
1 Mickey Mouse - Brave Little Prince *ICONIC*"""

        parsed_cards = []

        def collect_card(index, name, variant, quantity):
            parsed_cards.append(
                {
                    "index": index,
                    "name": name,
                    "variant": variant,
                    "quantity": quantity,
                }
            )

        parse_dreamborn_list(deck_text, collect_card)

        assert len(parsed_cards) == 2
        assert parsed_cards[0]["name"] == "Max Goof - Rockin' Teen"
        assert parsed_cards[0]["variant"] == CardVariant.EPIC
        assert parsed_cards[1]["name"] == "Mickey Mouse - Brave Little Prince"
        assert parsed_cards[1]["variant"] == CardVariant.ICONIC

    def test_parse_dreamborn_with_epic_shorthand(self):
        """Test parsing Dreamborn format with the *EP* epic shorthand marker."""
        deck_text = """1 Max Goof - Rockin' Teen *EP*"""

        parsed_cards = []

        def collect_card(index, name, variant, quantity):
            parsed_cards.append(
                {
                    "index": index,
                    "name": name,
                    "variant": variant,
                    "quantity": quantity,
                }
            )

        parse_dreamborn_list(deck_text, collect_card)

        assert len(parsed_cards) == 1
        assert parsed_cards[0]["name"] == "Max Goof - Rockin' Teen"
        assert parsed_cards[0]["variant"] == CardVariant.EPIC

    def test_parse_dreamborn_with_promo(self):
        """Test parsing Dreamborn format with promo marker."""
        deck_text = """1 Kuzco - Temperamental Emperor *PROMO*"""

        parsed_cards = []

        def collect_card(index, name, variant, quantity):
            parsed_cards.append(
                {
                    "index": index,
                    "name": name,
                    "variant": variant,
                    "quantity": quantity,
                }
            )

        parse_dreamborn_list(deck_text, collect_card)

        assert len(parsed_cards) == 1
        assert parsed_cards[0]["name"] == "Kuzco - Temperamental Emperor"
        assert parsed_cards[0]["variant"] == CardVariant.PROMO

    def test_parse_dreamborn_with_shorthand_markers(self):
        """Test parsing Dreamborn format with single-letter variant markers."""
        deck_text = """1 Mickey Mouse - Brave Little Prince *I*
1 Kuzco - Temperamental Emperor *P*"""

        parsed_cards = []

        def collect_card(index, name, variant, quantity):
            parsed_cards.append(
                {
                    "index": index,
                    "name": name,
                    "variant": variant,
                    "quantity": quantity,
                }
            )

        parse_dreamborn_list(deck_text, collect_card)

        assert len(parsed_cards) == 2
        assert parsed_cards[0]["name"] == "Mickey Mouse - Brave Little Prince"
        assert parsed_cards[0]["variant"] == CardVariant.ICONIC
        assert parsed_cards[1]["name"] == "Kuzco - Temperamental Emperor"
        assert parsed_cards[1]["variant"] == CardVariant.PROMO

    def test_parse_dreamborn_with_specific_print(self):
        """Test parsing Dreamborn format with a specific-print marker (set only)."""
        deck_text = """1 Mickey Mouse - True Friend *P1*"""

        parsed_cards = []

        def collect_card(index, name, variant, quantity):
            parsed_cards.append(
                {
                    "index": index,
                    "name": name,
                    "variant": variant,
                    "quantity": quantity,
                }
            )

        parse_dreamborn_list(deck_text, collect_card)

        assert len(parsed_cards) == 1
        assert parsed_cards[0]["name"] == "Mickey Mouse - True Friend"
        assert parsed_cards[0]["variant"] == "set:P1"

    def test_parse_dreamborn_with_specific_print_and_collector_number(self):
        """Test parsing Dreamborn format with a set + collector number marker."""
        deck_text = """1 Mickey Mouse - True Friend *P2-15*
1 Mickey Mouse - True Friend *P2-36*"""

        parsed_cards = []

        def collect_card(index, name, variant, quantity):
            parsed_cards.append(
                {
                    "index": index,
                    "name": name,
                    "variant": variant,
                    "quantity": quantity,
                }
            )

        parse_dreamborn_list(deck_text, collect_card)

        assert len(parsed_cards) == 2
        assert parsed_cards[0]["variant"] == "set:P2 cn:15"
        assert parsed_cards[1]["variant"] == "set:P2 cn:36"

    def test_parse_dreamborn_with_x_quantity(self):
        """Test parsing Dreamborn format with 'x' in quantity."""
        deck_text = """4x Pete - Games Referee
3x Merlin, Goat"""

        parsed_cards = []

        def collect_card(index, name, variant, quantity):
            parsed_cards.append(
                {
                    "index": index,
                    "name": name,
                    "quantity": quantity,
                }
            )

        parse_dreamborn_list(deck_text, collect_card)

        assert len(parsed_cards) == 2
        assert parsed_cards[0]["name"] == "Pete - Games Referee"
        assert parsed_cards[0]["quantity"] == 4


# --- Unit Tests for Utility Functions ---


class TestCommonUtilityFunctions:
    """Test utility functions."""

    def test_remove_nonalphanumeric(self):
        """Test removing non-alphanumeric characters."""
        assert remove_nonalphanumeric("Elsa, Spirit of Winter") == "ElsaSpiritofWinter"
        assert remove_nonalphanumeric("Anna - True-Hearted") == "AnnaTrueHearted"
        assert remove_nonalphanumeric("Magic Broom") == "MagicBroom"


class TestLorcastUtilityFunctions:
    """Test Lorcast utility functions."""

    def test_format_lorcast_query(self):
        """Test Lorcast query formatting."""
        query = format_lorcast_query("Elsa, Spirit of Winter", None)
        assert "+" in query
        assert "rarity:enchanted" not in query

        query_enchanted = format_lorcast_query(
            "Anna - True-Hearted", CardVariant.ENCHANTED.value
        )
        assert "rarity:enchanted" in query_enchanted

        query_epic = format_lorcast_query(
            "Max Goof - Rockin' Teen", CardVariant.EPIC.value
        )
        assert "rarity:epic" in query_epic

        query_iconic = format_lorcast_query(
            "Mickey Mouse - Brave Little Prince", CardVariant.ICONIC.value
        )
        assert "rarity:iconic" in query_iconic

        query_print = format_lorcast_query("Mickey Mouse - True Friend", "set:P2 cn:15")
        assert "set:P2" in query_print
        assert "cn:15" in query_print


class TestDreambornUtilityFunctions:
    """Test Dreamborn name and title formatting functions."""

    def test_format_dreamborn_name_comma_separator(self):
        """Test Dreamborn name extraction with comma separator."""
        assert format_dreamborn_name("Elsa, Spirit of Winter") == "Elsa"
        assert format_dreamborn_name("Mickey Mouse, True Friend") == "MickeyMouse"
        assert format_dreamborn_name("  Elsa, Spirit of Winter  ") == "Elsa"

    def test_format_dreamborn_name_hyphen_separator(self):
        """Test Dreamborn name extraction with hyphen separator."""
        assert format_dreamborn_name("Simba - King of the Pride Lands") == "Simba"
        assert format_dreamborn_name("Mickey Mouse - True Friend") == "MickeyMouse"
        assert format_dreamborn_name("  Simba - King  ") == "Simba"

    def test_format_dreamborn_name_colon_separator(self):
        """Test Dreamborn name extraction with colon separator."""
        assert format_dreamborn_name("Mickey Mouse: True Friend") == "MickeyMouse"
        assert format_dreamborn_name("Elsa: Spirit of Winter") == "Elsa"

    def test_format_dreamborn_name_no_separator(self):
        """Test Dreamborn name extraction with no separator."""
        assert format_dreamborn_name("Mulan") == "Mulan"
        assert format_dreamborn_name("  Mulan  ") == "Mulan"

    def test_format_dreamborn_name_special_characters(self):
        """Test Dreamborn name extraction with special characters."""
        assert format_dreamborn_name("Elsa, the Snow Queen!") == "Elsa"
        assert format_dreamborn_name("Simba - Lion King?") == "Simba"

    def test_format_dreamborn_title_comma_separator(self):
        """Test Dreamborn title extraction with comma separator."""
        assert format_dreamborn_title("Elsa, Spirit of Winter") == "SpiritofWinter"
        assert format_dreamborn_title("Mickey Mouse, True Friend") == "TrueFriend"

    def test_format_dreamborn_title_hyphen_separator(self):
        """Test Dreamborn title extraction with hyphen separator."""
        assert (
            format_dreamborn_title("Simba - King of the Pride Lands")
            == "KingofthePrideLands"
        )
        assert format_dreamborn_title("Mickey Mouse - True Friend") == "TrueFriend"

    def test_format_dreamborn_title_colon_separator(self):
        """Test Dreamborn title extraction with colon separator."""
        assert format_dreamborn_title("Mickey Mouse: True Friend") == "TrueFriend"
        assert format_dreamborn_title("Elsa: Spirit of Winter") == "SpiritofWinter"

    def test_format_dreamborn_title_no_separator(self):
        """Test Dreamborn title extraction with no separator."""
        assert format_dreamborn_title("Mulan") == ""
        assert format_dreamborn_title("Simba") == ""

    def test_format_dreamborn_title_special_characters(self):
        """Test Dreamborn title extraction with special characters."""
        assert format_dreamborn_title("Elsa, the Snow Queen!") == "theSnowQueen"
        assert format_dreamborn_title("Simba - Lion King?") == "LionKing"


# --- Integration Tests for API and Image Fetching ---


@pytest.mark.integration
class TestLorcastAPI:
    """Test Lorcast API requests."""

    def test_lorcast_api_availability(self):
        """Test that Lorcast API is available and responding."""
        response = request_lorcast("https://api.lorcast.com/v0/cards/search?q=Elsa")
        assert response.status_code == 200
        json_data = response.json()
        assert "results" in json_data

    def test_format_lorcast_query_epic(self):
        """Test that the epic variant resolves to the actual epic printing."""
        query = format_lorcast_query(
            "Aladdin - Barreling Through", CardVariant.EPIC.value
        )
        response = request_lorcast(f"https://api.lorcast.com/v0/cards/search?q={query}")
        card = response.json()["results"][0]
        assert card["rarity"] == "Epic"

    def test_format_lorcast_query_iconic(self):
        """Test that the iconic variant resolves to the actual iconic printing."""
        query = format_lorcast_query("Ariel - Ethereal Voice", CardVariant.ICONIC.value)
        response = request_lorcast(f"https://api.lorcast.com/v0/cards/search?q={query}")
        card = response.json()["results"][0]
        assert card["rarity"] == "Iconic"

    def test_format_lorcast_query_promo(self):
        """Test that the promo variant resolves to the actual promo printing."""
        query = format_lorcast_query(
            "Kuzco - Temperamental Emperor", CardVariant.PROMO.value
        )
        response = request_lorcast(f"https://api.lorcast.com/v0/cards/search?q={query}")
        card = response.json()["results"][0]
        assert card["rarity"] == "Promo"

    def test_format_lorcast_query_specific_print(self):
        """Test that a set + collector number marker resolves to the exact printing."""
        query = format_lorcast_query("Mickey Mouse - True Friend", "set:P2 cn:15")
        response = request_lorcast(f"https://api.lorcast.com/v0/cards/search?q={query}")
        card = response.json()["results"][0]
        assert card["set"]["code"] == "P2"
        assert card["collector_number"] == "15"


@pytest.mark.integration
class TestDreambornAPI:
    """Test Dreamborn API requests."""

    def test_dreamborn_api_availability(self):
        """Test that Dreamborn API is available and responding."""
        response = request_dreamborn(
            "https://dreamborn.ink/api/v2/cards?name=Elsa&title=Spirit+of+Winter"
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_dreamborn_api_card_with_title(self):
        """Test that we can fetch a card by name and title."""
        response = request_dreamborn(
            "https://dreamborn.ink/api/v2/cards?name=MickeyMouse&title=True+Friend"
        )
        assert response.status_code == 200
        cards = response.json()
        assert len(cards) > 0
        # Check that at least one card has the expected name
        card_names = [c.get("name", "").lower() for c in cards]
        assert any("mickey mouse" in name for name in card_names)

    def test_dreamborn_cdn_image_available(self):
        """Test that we can ping/fetch a card image from Dreamborn CDN."""
        # First, get a card from the API
        response = request_dreamborn(
            "https://dreamborn.ink/api/v2/cards?name=MickeyMouse&title=True+Friend"
        )
        assert response.status_code == 200
        cards = response.json()
        assert len(cards) > 0

        # Get the first card with a valid id
        card = None
        for c in cards:
            if c.get("id"):
                card = c
                break

        assert card is not None
        card_id = card["id"]
        card_language = card["language"]

        # Try to fetch the image from CDN
        image_url = f"https://cdn.dreamborn.ink/images/{card_language}/cards/{card_id}"
        image_response = request_dreamborn(image_url)
        assert image_response.status_code == 200
        assert len(image_response.content) > 0


@pytest.mark.integration
class TestLorcastFullFetchWorkflow:
    """Integration tests for the complete card fetching workflow using Lorcast."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for test output."""
        front_dir = tempfile.mkdtemp()
        yield front_dir
        shutil.rmtree(front_dir)

    def test_fetch_single_card(self, temp_dirs):
        """Test fetching a single Lorcana card."""
        front_dir = temp_dirs

        # Use a very small decklist - just 1 card
        deck_text = "1 Elsa, Spirit of Winter"

        handle_card = lorcast_get_handle_card(front_dir)
        parse_deck(deck_text, DeckFormat.DREAMBORN, handle_card)

        # Check that at least one image was created
        files = os.listdir(front_dir)
        assert len(files) >= 1

        # Verify image file has content (> 0 bytes)
        for f in files:
            file_path = os.path.join(front_dir, f)
            assert os.path.getsize(file_path) > 0

    def test_fetch_with_quantity(self, temp_dirs):
        """Test fetching cards with quantity > 1."""
        front_dir = temp_dirs

        deck_text = "2 Magic Broom, Illuminary Keeper"

        handle_card = lorcast_get_handle_card(front_dir)
        parse_deck(deck_text, DeckFormat.DREAMBORN, handle_card)

        # Should have 2 copies of the card
        files = os.listdir(front_dir)
        assert len(files) == 2

        for f in files:
            file_path = os.path.join(front_dir, f)
            assert os.path.getsize(file_path) > 0


@pytest.mark.integration
class TestDreambornFullFetchWorkflow:
    """Integration tests for the complete card fetching workflow using Dreamborn."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for test output."""
        front_dir = tempfile.mkdtemp()
        yield front_dir
        shutil.rmtree(front_dir)

    def test_fetch_single_card(self, temp_dirs):
        """Test fetching a single Lorcana card using Dreamborn."""
        front_dir = temp_dirs

        # Use a very small decklist - just 1 card
        deck_text = "1 Elsa, Spirit of Winter"

        handle_card = dreamborn_get_handle_card(front_dir)
        parse_deck(deck_text, DeckFormat.DREAMBORN, handle_card)

        # Check that at least one image was created
        files = os.listdir(front_dir)
        assert len(files) >= 1

        # Verify image file has content (> 0 bytes)
        for f in files:
            file_path = os.path.join(front_dir, f)
            assert os.path.getsize(file_path) > 0

    def test_fetch_with_quantity(self, temp_dirs):
        """Test fetching cards with quantity > 1 using Dreamborn."""
        front_dir = temp_dirs

        deck_text = "2 Magic Broom, Illuminary Keeper"

        handle_card = dreamborn_get_handle_card(front_dir)
        parse_deck(deck_text, DeckFormat.DREAMBORN, handle_card)

        # Should have 2 copies of the card
        files = os.listdir(front_dir)
        assert len(files) == 2

        for f in files:
            file_path = os.path.join(front_dir, f)
            assert os.path.getsize(file_path) > 0
