"""
Tests for the MTG plugin.
Tests deck format parsing and image fetching from Scryfall.
"""
import os
import shutil
import tempfile
import warnings
import pytest
import requests
from unittest.mock import patch, MagicMock

from plugins.mtg.deck_formats import (
    DeckFormat,
    parse_deck,
    parse_simple_list,
    parse_mtga,
    parse_mtgo,
    parse_archidekt,
    parse_deckstats,
    parse_moxfield,
    parse_scryfall_json,
    parse_mpcfill_xml,
    extract_mpcfill_cardback_id,
)
from plugins.mtg.common import ScryfallLanguage, to_scryfall_api_lang
from plugins.mtg.mpcfill import CARDBACK_STEM, MPCFillFetcher, write_image
from plugins.mtg.scryfall import request_scryfall, get_handle_card, fetch_card, fetch_printings, build_image_url, fetch_image
from typing import List
from plugins.mtg.patterns import MOXFIELD_PATTERN, DECKSTATS_PATTERN

# --- Unit Tests for Deck Format Parsing ---

class TestDeckFormatParsing:
    """Test regex pattern matching for special deck format cases."""

    def test_star_symbol_in_collector_number(self):
        """Test that Moxfield star symbol in collector numbers is matched."""
        # Moxfield exports can include ★ in collector numbers for special versions
        line = "1 Sol Ring (SLD) 123★"
        match = MOXFIELD_PATTERN.match(line)

        assert match is not None
        assert match.group(1) == "1"
        assert match.group(2) == "Sol Ring"
        assert match.group(3) == "SLD"
        assert match.group(4) == "123★"


    def test_collector_number_with_dash(self):
        """Test that collector numbers with dashes are matched."""
        # Collector numbers like "123-456" should also be captured
        line = "1 Some Card (SET) 123-456"
        match = MOXFIELD_PATTERN.match(line)

        assert match is not None
        assert match.group(4) == "123-456"


    def test_quantity_with_x(self):
        """Test that quantities with "x" suffix are matched."""
        # Moxfield format can include "x" after quantity (e.g. "4x")
        line = "4x Lightning Bolt (2XM) 117"
        match = MOXFIELD_PATTERN.match(line)

        assert match is not None
        assert match.group(1) == "4"
        assert match.group(2) == "Lightning Bolt"
        assert match.group(3) == "2XM"
        assert match.group(4) == "117"


    def test_deckstats_star_symbol_in_collector_number(self):
        """Test that Deckstats star symbol in collector numbers is matched."""
        # Deckstats can include ★ in collector numbers
        # e.g. "1 [SLD#1494★] Sol Ring"
        line = "1 [SLD#1494★] Sol Ring"
        match = DECKSTATS_PATTERN.match(line)

        assert match is not None
        assert match.group(1) == "1"
        assert match.group(2) == "SLD"
        assert match.group(3) == "1494★"
        assert match.group(4) == "Sol Ring"

class TestSimpleFormat:
    """Test the simple card name list format."""

    def test_parse_simple_list(self):
        """Test parsing a simple list of card names."""
        deck_text = """Isshin, Two Heavens as One
Arid Mesa
Battlefield Forge"""

        parsed_cards = []
        def collect_card(index, name, set_code, collector_number, quantity):
            parsed_cards.append({
                'index': index,
                'name': name,
                'set_code': set_code,
                'collector_number': collector_number,
                'quantity': quantity
            })

        parse_simple_list(deck_text, collect_card)

        assert len(parsed_cards) == 3
        assert parsed_cards[0]['name'] == "Isshin, Two Heavens as One"
        assert parsed_cards[0]['quantity'] == 1
        assert parsed_cards[1]['name'] == "Arid Mesa"
        assert parsed_cards[2]['name'] == "Battlefield Forge"


class TestMTGAFormat:
    """Test MTG Arena format parsing."""

    def test_parse_mtga_with_set_info(self):
        """Test parsing MTGA format with set and collector number."""
        deck_text = """Deck
2 Arid Mesa (MH2) 244
1 Lion Sash (NEO) 26"""

        parsed_cards = []
        def collect_card(index, name, set_code, collector_number, quantity):
            parsed_cards.append({
                'index': index,
                'name': name,
                'set_code': set_code,
                'collector_number': collector_number,
                'quantity': quantity
            })

        parse_mtga(deck_text, collect_card)

        assert len(parsed_cards) == 2
        assert parsed_cards[0]['name'] == "Arid Mesa"
        assert parsed_cards[0]['set_code'] == "MH2"
        assert parsed_cards[0]['collector_number'] == "244"
        assert parsed_cards[0]['quantity'] == 2

    def test_parse_mtga_without_set_info(self):
        """Test parsing MTGA format without set information."""
        deck_text = """Deck
2x Mountain
1 Lightning Bolt"""

        parsed_cards = []
        def collect_card(index, name, set_code, collector_number, quantity):
            parsed_cards.append({
                'index': index,
                'name': name,
                'set_code': set_code,
                'collector_number': collector_number,
                'quantity': quantity
            })

        parse_mtga(deck_text, collect_card)

        assert len(parsed_cards) == 2
        assert parsed_cards[0]['name'] == "Mountain"
        assert parsed_cards[0]['set_code'] == ""


class TestMTGOFormat:
    """Test MTG Online format parsing."""

    def test_parse_mtgo(self):
        """Test parsing MTGO format."""
        deck_text = """1 Ainok Bond-Kin
2 Witch Enchanter

SIDEBOARD:
1 Containment Priest"""

        parsed_cards = []
        def collect_card(index, name, set_code, collector_number, quantity):
            parsed_cards.append({
                'index': index,
                'name': name,
                'quantity': quantity
            })

        parse_mtgo(deck_text, collect_card)

        assert len(parsed_cards) == 3
        assert parsed_cards[0]['name'] == "Ainok Bond-Kin"
        assert parsed_cards[0]['quantity'] == 1
        assert parsed_cards[1]['name'] == "Witch Enchanter"
        assert parsed_cards[1]['quantity'] == 2


class TestArchidektFormat:
    """Test Archidekt format parsing."""

    def test_parse_archidekt(self):
        """Test parsing Archidekt format with tags and foil markers."""
        deck_text = """1x Agadeem's Awakening // Agadeem, the Undercrypt (znr) 90 [Resilience,Land]
1x Ashnod's Altar (ema) 218 *F* [Mana Advantage]"""

        parsed_cards = []
        def collect_card(index, name, set_code, collector_number, quantity):
            parsed_cards.append({
                'index': index,
                'name': name,
                'set_code': set_code,
                'collector_number': collector_number,
                'quantity': quantity
            })

        parse_archidekt(deck_text, collect_card)

        assert len(parsed_cards) == 2
        assert parsed_cards[0]['name'] == "Agadeem's Awakening // Agadeem, the Undercrypt"
        assert parsed_cards[0]['set_code'] == "znr"
        assert parsed_cards[0]['collector_number'] == "90"


class TestDeckstatsFormat:
    """Test Deckstats format parsing."""

    def test_parse_deckstats_with_set(self):
        """Test parsing Deckstats format with set info."""
        deck_text = """//Main
1 [2XM#310] Ash Barrens
1 Blinkmoth Nexus"""

        parsed_cards = []
        def collect_card(index, name, set_code, collector_number, quantity):
            parsed_cards.append({
                'index': index,
                'name': name,
                'set_code': set_code,
                'collector_number': collector_number,
                'quantity': quantity
            })

        parse_deckstats(deck_text, collect_card)

        assert len(parsed_cards) == 2
        assert parsed_cards[0]['name'] == "Ash Barrens"
        assert parsed_cards[0]['set_code'] == "2XM"
        assert parsed_cards[0]['collector_number'] == "310"
        assert parsed_cards[1]['name'] == "Blinkmoth Nexus"
        assert parsed_cards[1]['set_code'] == ""

    def test_strips_commander_annotation(self):
        """Test that #!Commander annotation is stripped from card names."""
        deck_text = "1 Varragoth, Bloodsky Sire #!Commander"

        parsed_cards = []
        def collect_card(index, name, set_code, collector_number, quantity):
            parsed_cards.append({'index': index, 'name': name, 'set_code': set_code, 'collector_number': collector_number, 'quantity': quantity})

        parse_deckstats(deck_text, collect_card)

        assert len(parsed_cards) == 1
        assert parsed_cards[0]['name'] == "Varragoth, Bloodsky Sire"
        assert parsed_cards[0]['quantity'] == 1


class TestMoxfieldFormat:
    """Test Moxfield format parsing."""

    def test_parse_moxfield(self):
        """Test parsing Moxfield format."""
        deck_text = """1 Ainok Bond-Kin (2X2) 5
2 Witch Enchanter // Witch-Blessed Meadow (MH3) 239"""

        parsed_cards = []
        def collect_card(index, name, set_code, collector_number, quantity):
            parsed_cards.append({
                'index': index,
                'name': name,
                'set_code': set_code,
                'collector_number': collector_number,
                'quantity': quantity
            })

        parse_moxfield(deck_text, collect_card)

        assert len(parsed_cards) == 2
        assert parsed_cards[0]['name'] == "Ainok Bond-Kin"
        assert parsed_cards[0]['set_code'] == "2X2"
        assert parsed_cards[1]['name'] == "Witch Enchanter // Witch-Blessed Meadow"


class TestScryfallJsonFormat:
    """Test Scryfall JSON format parsing."""

    def test_parse_scryfall_json_without_image_uris(self):
        """Without image_uris, cards are dispatched through handle_card."""
        deck_text = """{
  "entries": {
    "mainboard": [
      {
        "count": 2,
        "card_digest": {
          "name": "Lightning Bolt",
          "collector_number": "141",
          "set": "clu"
        }
      }
    ]
  }
}"""

        parsed_cards = []
        def collect_card(index, name, set_code, collector_number, quantity):
            parsed_cards.append({
                'index': index,
                'name': name,
                'set_code': set_code,
                'collector_number': collector_number,
                'quantity': quantity
            })

        parse_scryfall_json(deck_text, collect_card)

        assert len(parsed_cards) == 1
        assert parsed_cards[0]['name'] == "Lightning Bolt"
        assert parsed_cards[0]['set_code'] == "clu"
        assert parsed_cards[0]['quantity'] == 2

    @patch('plugins.mtg.deck_formats.requests.get')
    def test_parse_scryfall_json_with_image_uris_fetches_directly(self, mock_get, tmp_path):
        """When image_uris.front is present, the image is fetched directly and handle_card is not called."""
        mock_response = MagicMock()
        mock_response.content = b'fake_image_data'
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        deck_text = """{
  "entries": {
    "mainboard": [
      {
        "count": 2,
        "card_digest": {
          "name": "Formidable Speaker",
          "collector_number": "176",
          "set": "ecl",
          "image_uris": {
            "front": "https://cards.scryfall.io/large/front/9/3/93ac8c22.jpg"
          }
        }
      }
    ]
  }
}"""

        handle_card = MagicMock()
        front_dir = str(tmp_path / "front")
        os.makedirs(front_dir)

        parse_scryfall_json(deck_text, handle_card, front_dir, '')

        handle_card.assert_not_called()
        mock_get.assert_called_once_with(
            "https://cards.scryfall.io/large/front/9/3/93ac8c22.jpg",
            headers={'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'}
        )
        saved_files = os.listdir(front_dir)
        assert len(saved_files) == 2  # quantity=2

    @patch('plugins.mtg.deck_formats.requests.get')
    def test_parse_scryfall_json_with_image_uris_back(self, mock_get, tmp_path):
        """When image_uris.back is present, both front and back images are fetched."""
        mock_response = MagicMock()
        mock_response.content = b'fake_image_data'
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        deck_text = """{
  "entries": {
    "mainboard": [
      {
        "count": 1,
        "card_digest": {
          "name": "Delver of Secrets",
          "collector_number": "51",
          "set": "isd",
          "image_uris": {
            "front": "https://cards.scryfall.io/large/front/a/b/front.jpg",
            "back": "https://cards.scryfall.io/large/back/a/b/back.jpg"
          }
        }
      }
    ]
  }
}"""

        front_dir = str(tmp_path / "front")
        back_dir = str(tmp_path / "back")
        os.makedirs(front_dir)
        os.makedirs(back_dir)

        parse_scryfall_json(deck_text, MagicMock(), front_dir, back_dir)

        fetched_urls = [call[0][0] for call in mock_get.call_args_list]
        assert any("front.jpg" in url for url in fetched_urls)
        assert any("back.jpg" in url for url in fetched_urls)
        assert len(os.listdir(front_dir)) == 1
        assert len(os.listdir(back_dir)) == 1



# --- Unit Tests for Scryfall Fetching ---

SHADOWSPEAR_JSON = {
    'name': 'Shadowspear',
    'set': 'pza',
    'collector_number': '17',
    'layout': 'normal',
}

PRINTS_SEARCH_URI = 'https://api.scryfall.com/cards/search?q=oracleid%3Atest&unique=prints'

# Skrelv has both a Universe Beyond printing (SLD) and a standard printing (ONE).
SKRELV_JSON = {
    'name': 'Skrelv, Defector Mite',
    'set': 'one',
    'collector_number': '225',
    'layout': 'normal',
    'prints_search_uri': PRINTS_SEARCH_URI,
}
SKRELV_UB_PRINTING = {
    'set': 'sld', 'collector_number': '1926',
    'nonfoil': True, 'digital': False, 'promo': False,
    'full_art': False, 'border_color': 'black', 'frame_effects': [],
}
SKRELV_NON_UB_PRINTING = {
    'set': 'one', 'collector_number': '225',
    'nonfoil': True, 'digital': False, 'promo': False,
    'full_art': False, 'border_color': 'black', 'frame_effects': [],
}

# Excalibur only exists as a Universe Beyond card.
EXCALIBUR_JSON = {
    'name': 'Excalibur, Sword of Eden',
    'set': 'acr',
    'collector_number': '72',
    'layout': 'normal',
    'prints_search_uri': PRINTS_SEARCH_URI,
}
EXCALIBUR_PRINTING = {
    'set': 'acr', 'collector_number': '72',
    'nonfoil': True, 'digital': False, 'promo': False,
    'full_art': False, 'border_color': 'black', 'frame_effects': [],
}

def make_404():
    err = requests.exceptions.HTTPError()
    err.response = MagicMock()
    err.response.status_code = 404
    return err

class TestFetchPrintingsUB:
    """Unit tests for Universe Beyond filtering in fetch_printings."""

    @patch('plugins.mtg.scryfall.request_scryfall')
    def test_prefer_ub_returns_ub_printings_when_available(self, mock_request):
        """prefer_ub=True fetches with is:ub filter and returns those results."""
        ub_response = MagicMock()
        ub_response.json.return_value = {'data': [SKRELV_UB_PRINTING]}
        mock_request.return_value = ub_response

        result = fetch_printings(PRINTS_SEARCH_URI, True, 'Skrelv, Defector Mite')

        assert result == [SKRELV_UB_PRINTING]
        called_url = mock_request.call_args_list[0][0][0]
        assert 'is%3Aub' in called_url or 'is:ub' in called_url

    @patch('plugins.mtg.scryfall.request_scryfall')
    def test_ignore_ub_returns_non_ub_printings_when_available(self, mock_request):
        """ignore_ub=True fetches with -is:ub filter and returns those results."""
        non_ub_response = MagicMock()
        non_ub_response.json.return_value = {'data': [SKRELV_NON_UB_PRINTING]}
        mock_request.return_value = non_ub_response

        result = fetch_printings(PRINTS_SEARCH_URI, False, 'Skrelv, Defector Mite')

        assert result == [SKRELV_NON_UB_PRINTING]
        called_url = mock_request.call_args_list[0][0][0]
        assert '-is%3Aub' in called_url or '-is:ub' in called_url

    @patch('plugins.mtg.scryfall.request_scryfall')
    def test_prefer_ub_falls_back_when_no_ub_printings(self, mock_request):
        """prefer_ub=True falls back to all printings when no UB printings exist."""
        ub_response = MagicMock()
        ub_response.json.return_value = {'data': []}
        fallback_response = MagicMock()
        fallback_response.json.return_value = {'data': [EXCALIBUR_PRINTING]}
        mock_request.side_effect = [ub_response, fallback_response]

        result = fetch_printings(PRINTS_SEARCH_URI, True, 'Excalibur, Sword of Eden')

        assert result == [EXCALIBUR_PRINTING]
        assert mock_request.call_count == 2

    @patch('plugins.mtg.scryfall.request_scryfall')
    def test_ignore_ub_falls_back_when_all_printings_are_ub(self, mock_request):
        """ignore_ub=True falls back to all printings when no non-UB printings exist."""
        non_ub_response = MagicMock()
        non_ub_response.json.return_value = {'data': []}
        fallback_response = MagicMock()
        fallback_response.json.return_value = {'data': [EXCALIBUR_PRINTING]}
        mock_request.side_effect = [non_ub_response, fallback_response]

        result = fetch_printings(PRINTS_SEARCH_URI, False, 'Excalibur, Sword of Eden')

        assert result == [EXCALIBUR_PRINTING]
        assert mock_request.call_count == 2

    @patch('plugins.mtg.scryfall.request_scryfall')
    def test_no_ub_filter_fetches_all_printings(self, mock_request):
        """prefer_ub=None skips the filtered request entirely."""
        all_response = MagicMock()
        all_response.json.return_value = {'data': [SKRELV_UB_PRINTING, SKRELV_NON_UB_PRINTING]}
        mock_request.return_value = all_response

        result = fetch_printings(PRINTS_SEARCH_URI, None, 'Skrelv, Defector Mite')

        assert result == [SKRELV_UB_PRINTING, SKRELV_NON_UB_PRINTING]
        assert mock_request.call_count == 1
        assert mock_request.call_args_list[0][0][0] == PRINTS_SEARCH_URI


class TestFetchCardUB:
    """Unit tests for prefer_ub/ignore_ub integration inside fetch_card."""

    def named_response(self, card_json):
        r = MagicMock()
        r.json.return_value = card_json
        return r

    def printings_response(self, printings):
        r = MagicMock()
        r.json.return_value = {'data': printings}
        return r

    @patch('plugins.mtg.scryfall.fetch_card_art')
    @patch('plugins.mtg.scryfall.request_scryfall')
    def test_prefer_ub_selects_ub_printing(self, mock_request, mock_fetch_art):
        """With prefer_ub=True, the UB printing is selected over the standard one."""
        mock_request.side_effect = [
            self.named_response(SKRELV_JSON),           # /cards/named
            self.printings_response([SKRELV_UB_PRINTING]),  # is:ub filtered search
        ]

        fetch_card(1, 1, "", "", False, "Skrelv, Defector Mite",
                   False, set(), set(), False, False, True, False, None, False,
                   front_img_dir='front', double_sided_dir='double_sided')

        args, _ = mock_fetch_art.call_args
        assert args[3] == 'sld'
        assert args[4] == '1926'

    @patch('plugins.mtg.scryfall.fetch_card_art')
    @patch('plugins.mtg.scryfall.request_scryfall')
    def test_ignore_ub_selects_non_ub_printing(self, mock_request, mock_fetch_art):
        """With ignore_ub=True, the non-UB printing is selected."""
        mock_request.side_effect = [
            self.named_response(SKRELV_JSON),                    # /cards/named
            self.printings_response([SKRELV_NON_UB_PRINTING]),   # -is:ub filtered search
        ]

        fetch_card(1, 1, "", "", False, "Skrelv, Defector Mite",
                   False, set(), set(), False, False, False, True, None, False,
                   front_img_dir='front', double_sided_dir='double_sided')

        args, _ = mock_fetch_art.call_args
        assert args[3] == 'one'
        assert args[4] == '225'

    @patch('plugins.mtg.scryfall.fetch_card_art')
    @patch('plugins.mtg.scryfall.request_scryfall')
    def test_prefer_ub_falls_back_for_ub_only_card(self, mock_request, mock_fetch_art):
        """With prefer_ub=True on a UB-only card, the UB printing is used after fallback."""
        mock_request.side_effect = [
            self.named_response(EXCALIBUR_JSON),            # /cards/named
            self.printings_response([]),                     # is:ub → empty (no non-UB)
            self.printings_response([EXCALIBUR_PRINTING]),  # fallback to all printings
        ]

        fetch_card(1, 1, "", "", False, "Excalibur, Sword of Eden",
                   False, set(), set(), False, False, True, False, None, False,
                   front_img_dir='front', double_sided_dir='double_sided')

        args, _ = mock_fetch_art.call_args
        assert args[3] == 'acr'
        assert args[4] == '72'


class TestScryfallFetch:
    """Unit tests for Scryfall card fetching logic."""

    @patch('plugins.mtg.scryfall.fetch_card_art')
    @patch('plugins.mtg.scryfall.request_scryfall')
    def test_flavor_name_card_is_fetched(self, mock_request, mock_fetch_art):
        """A card known only by its flavor name still has its art fetched successfully."""
        search_response = MagicMock()
        search_response.json.return_value = {'data': [SHADOWSPEAR_JSON]}
        mock_request.side_effect = [make_404(), search_response]

        fetch_card(1, 1, "", "", False, "Donnie's Bō",
                   False, set(), set(), False, False, False, False, None, False,
                   front_img_dir='front', double_sided_dir='double_sided')

        mock_fetch_art.assert_called_once()

    @patch('plugins.mtg.scryfall.session.get')
    def test_image_fetched_with_lowercase_set_code(self, mock_get):
        """When given an uppercase set code, the image is fetched using the lowercase code returned by the API."""
        info_response = MagicMock(status_code=200)
        info_response.raise_for_status.return_value = None
        info_response.json.return_value = {
            'name': 'Felidar Retreat',
            'set': 'fdn',
            'collector_number': '574',
            'layout': 'normal',
        }
        image_response = MagicMock(status_code=200)
        image_response.raise_for_status.return_value = None
        image_response.content = b'fake_image'

        mock_get.side_effect = [info_response, image_response]

        with patch('builtins.open', MagicMock()):
            fetch_card(1, 1, "FDN", "574", False, "Felidar Retreat",
                       False, set(), set(), False, False, False, False, None, False,
                       front_img_dir='front', double_sided_dir='double_sided')

        # call_args_list is a list of all calls made to mock_get, in order.
        # [1]    → the second call (index 1), which is the image fetch (after the card info fetch)
        # [0]    → the positional args tuple for that call
        # [0]    → the first positional argument, which is the URL string
        image_url = mock_get.call_args_list[1][0][0]
        assert '/fdn/' in image_url
        assert '/FDN/' not in image_url

    @patch('plugins.mtg.scryfall.fetch_card_art')
    @patch('plugins.mtg.scryfall.request_scryfall')
    def test_found_by_exact_name_does_not_call_flavor_search(self, mock_request, mock_fetch_art):
        """When a card is found by its exact name, no additional flavor name search is made."""
        named_response = MagicMock()
        named_response.json.return_value = SHADOWSPEAR_JSON
        mock_request.return_value = named_response

        fetch_card(1, 1, "", "", False, "Shadowspear",
                   False, set(), set(), False, False, False, False, None, False,
                   front_img_dir='front', double_sided_dir='double_sided')

        # Build a list of every URL string passed to request_scryfall across all calls.
        # call_args_list → list of calls, one per request_scryfall invocation
        # call[0]        → positional args tuple for that call
        # call[0][0]     → first positional argument, which is the URL string
        called_urls = [call[0][0] for call in mock_request.call_args_list]
        assert not any('flavor_name' in url for url in called_urls)
        mock_fetch_art.assert_called_once()


# --- Unit Tests for Language Support ---

class TestScryfallLanguageEnum:
    """Test ScryfallLanguage enum values and mapping to Scryfall API codes."""

    def test_all_printed_codes_present(self):
        """All supported printed codes are present in the enum."""
        expected_printed_codes = {"en", "sp", "fr", "de", "it", "pt", "jp", "kr", "ru", "cs", "ct", "ag", "ph"}
        actual_codes = {lang.value for lang in ScryfallLanguage}
        assert actual_codes == expected_printed_codes

    def test_enum_values_are_printed_codes(self):
        """Enum values match the Scryfall printed code column."""
        assert ScryfallLanguage.ENGLISH.value == "en"
        assert ScryfallLanguage.SPANISH.value == "sp"
        assert ScryfallLanguage.FRENCH.value == "fr"
        assert ScryfallLanguage.GERMAN.value == "de"
        assert ScryfallLanguage.ITALIAN.value == "it"
        assert ScryfallLanguage.PORTUGUESE.value == "pt"
        assert ScryfallLanguage.JAPANESE.value == "jp"
        assert ScryfallLanguage.KOREAN.value == "kr"
        assert ScryfallLanguage.RUSSIAN.value == "ru"
        assert ScryfallLanguage.SIMPLIFIED_CHINESE.value == "cs"
        assert ScryfallLanguage.TRADITIONAL_CHINESE.value == "ct"
        assert ScryfallLanguage.ANCIENT_GREEK.value == "ag"
        assert ScryfallLanguage.PHYREXIAN.value == "ph"

    def test_to_scryfall_api_lang_non_trivial_mappings(self):
        """Printed codes that differ from the Scryfall API code are mapped correctly."""
        assert to_scryfall_api_lang(ScryfallLanguage.SPANISH)           == "es"
        assert to_scryfall_api_lang(ScryfallLanguage.JAPANESE)          == "ja"
        assert to_scryfall_api_lang(ScryfallLanguage.KOREAN)            == "ko"
        assert to_scryfall_api_lang(ScryfallLanguage.SIMPLIFIED_CHINESE)  == "zhs"
        assert to_scryfall_api_lang(ScryfallLanguage.TRADITIONAL_CHINESE) == "zht"
        assert to_scryfall_api_lang(ScryfallLanguage.ANCIENT_GREEK)     == "grc"

    def test_to_scryfall_api_lang_identity_mappings(self):
        """Printed codes that are the same as the Scryfall API code pass through unchanged."""
        for lang in (ScryfallLanguage.ENGLISH, ScryfallLanguage.FRENCH, ScryfallLanguage.GERMAN,
                     ScryfallLanguage.ITALIAN, ScryfallLanguage.PORTUGUESE, ScryfallLanguage.RUSSIAN,
                     ScryfallLanguage.PHYREXIAN):
            assert to_scryfall_api_lang(lang) == lang.value

    def test_construct_via_printed_code(self):
        """ScryfallLanguage can be constructed from a printed code string."""
        assert ScryfallLanguage("jp") == ScryfallLanguage.JAPANESE
        assert ScryfallLanguage("cs") == ScryfallLanguage.SIMPLIFIED_CHINESE


class TestBuildImageUrl:
    """Test URL construction for different language preferences."""

    def test_english_produces_default_url(self):
        url = build_image_url("lea", "1", ScryfallLanguage.ENGLISH)
        assert url == "https://api.scryfall.com/cards/lea/1/?format=image&version=png"
        assert "/en?" not in url

    def test_none_produces_default_url(self):
        url = build_image_url("lea", "1", None)
        assert url == "https://api.scryfall.com/cards/lea/1/?format=image&version=png"

    def test_non_english_embeds_api_lang_code(self):
        url = build_image_url("lea", "1", ScryfallLanguage.JAPANESE)
        assert url == "https://api.scryfall.com/cards/lea/1/ja?format=image&version=png"

    def test_spanish_uses_api_code_not_printed_code(self):
        """Printed code 'sp' must map to API code 'es' in the URL."""
        url = build_image_url("lea", "1", ScryfallLanguage.SPANISH)
        assert "/es?" in url
        assert "/sp?" not in url

    def test_simplified_chinese_uses_zhs(self):
        url = build_image_url("lea", "1", ScryfallLanguage.SIMPLIFIED_CHINESE)
        assert "/zhs?" in url


class TestFetchImageLanguageFallback:
    """Test that fetch_image tries langs in priority order, falling back to English."""

    @patch('plugins.mtg.scryfall.request_scryfall')
    def test_falls_back_to_english_on_404(self, mock_request):
        lang_404 = requests.exceptions.HTTPError()
        lang_404.response = MagicMock()
        lang_404.response.status_code = 404

        english_response = MagicMock()
        english_response.content = b'fake_english_image'
        mock_request.side_effect = [lang_404, english_response]

        result = fetch_image("neo", "26", [ScryfallLanguage.JAPANESE])

        assert result == b'fake_english_image'
        assert mock_request.call_count == 2
        fallback_url = mock_request.call_args_list[1][0][0]
        assert "/ja?" not in fallback_url
        assert "neo/26/" in fallback_url

    @patch('plugins.mtg.scryfall.request_scryfall')
    def test_tries_priority_order_before_english(self, mock_request):
        """With [jp, de], tries jp → de → en, returning first success."""
        err_404 = requests.exceptions.HTTPError()
        err_404.response = MagicMock()
        err_404.response.status_code = 404

        de_response = MagicMock()
        de_response.content = b'fake_german_image'
        mock_request.side_effect = [err_404, de_response]

        result = fetch_image("lea", "1", [ScryfallLanguage.JAPANESE, ScryfallLanguage.GERMAN])

        assert result == b'fake_german_image'
        assert mock_request.call_count == 2
        second_url = mock_request.call_args_list[1][0][0]
        assert "/de?" in second_url

    @patch('plugins.mtg.scryfall.request_scryfall')
    def test_raises_when_all_langs_404(self, mock_request):
        """Raises the last HTTPError when every language including English 404s."""
        err_404 = requests.exceptions.HTTPError()
        err_404.response = MagicMock()
        err_404.response.status_code = 404
        mock_request.side_effect = err_404

        with pytest.raises(requests.exceptions.HTTPError):
            fetch_image("lea", "1", [ScryfallLanguage.JAPANESE])

        assert mock_request.call_count == 2  # jp + en fallback

    @patch('plugins.mtg.scryfall.request_scryfall')
    def test_does_not_fall_back_on_non_404_error(self, mock_request):
        err_500 = requests.exceptions.HTTPError()
        err_500.response = MagicMock()
        err_500.response.status_code = 500
        mock_request.side_effect = err_500

        with pytest.raises(requests.exceptions.HTTPError):
            fetch_image("neo", "26", [ScryfallLanguage.JAPANESE])

        assert mock_request.call_count == 1

    @patch('plugins.mtg.scryfall.request_scryfall')
    def test_english_only_does_not_retry_on_404(self, mock_request):
        err_404 = requests.exceptions.HTTPError()
        err_404.response = MagicMock()
        err_404.response.status_code = 404
        mock_request.side_effect = err_404

        with pytest.raises(requests.exceptions.HTTPError):
            fetch_image("lea", "1", [ScryfallLanguage.ENGLISH])

        assert mock_request.call_count == 1

    @patch('plugins.mtg.scryfall.request_scryfall')
    def test_no_langs_falls_back_to_english(self, mock_request):
        english_response = MagicMock()
        english_response.content = b'fake_english_image'
        mock_request.return_value = english_response

        result = fetch_image("lea", "1", None)

        assert result == b'fake_english_image'
        url = mock_request.call_args_list[0][0][0]
        assert "/en?" not in url  # English uses the default URL form


class TestFetchCardWithLanguage:
    """Test that fetch_card passes prefer_langs through to fetch_card_art."""

    @patch('plugins.mtg.scryfall.fetch_card_art')
    @patch('plugins.mtg.scryfall.request_scryfall')
    def test_prefer_langs_passed_to_fetch_card_art(self, mock_request, mock_fetch_art):
        shadowspear_with_prints = {**SHADOWSPEAR_JSON, 'prints_search_uri': PRINTS_SEARCH_URI}
        named_response = MagicMock()
        named_response.json.return_value = shadowspear_with_prints
        printings_response = MagicMock()
        printings_response.json.return_value = {'data': [
            {**SKRELV_NON_UB_PRINTING, 'set': 'pza', 'collector_number': '17', 'lang': 'ja'},
        ]}
        mock_request.side_effect = [named_response, printings_response]

        langs = [ScryfallLanguage.JAPANESE, ScryfallLanguage.GERMAN]
        fetch_card(1, 1, "", "", False, "Shadowspear",
                   False, set(), set(), False, False, False, False, langs, False,
                   front_img_dir='front', double_sided_dir='double_sided')

        args, _ = mock_fetch_art.call_args
        assert args[8] == langs

    @patch('plugins.mtg.scryfall.fetch_card_art')
    @patch('plugins.mtg.scryfall.request_scryfall')
    def test_no_langs_defaults_to_none(self, mock_request, mock_fetch_art):
        named_response = MagicMock()
        named_response.json.return_value = SHADOWSPEAR_JSON
        mock_request.return_value = named_response

        fetch_card(1, 1, "", "", False, "Shadowspear",
                   False, set(), set(), False, False, False, False, None, False,
                   front_img_dir='front', double_sided_dir='double_sided')

        args, _ = mock_fetch_art.call_args
        assert args[8] is None


# --- Integration Tests for API and Image Fetching ---

@pytest.mark.integration
class TestScryfallAPI:
    """Test Scryfall API requests."""

    def test_scryfall_api_availability(self):
        """Test that Scryfall API is available and responding."""
        response = request_scryfall("https://api.scryfall.com/cards/named?exact=Lightning+Bolt")
        assert response.status_code == 200
        json_data = response.json()
        assert json_data.get('name') == "Lightning Bolt"


@pytest.mark.integration
class TestFullFetchWorkflow:
    """Integration tests for the complete card fetching workflow."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for test output."""
        front_dir = tempfile.mkdtemp()
        double_sided_dir = tempfile.mkdtemp()
        yield front_dir, double_sided_dir
        shutil.rmtree(front_dir)
        shutil.rmtree(double_sided_dir)

    def test_fetch_single_card_simple_format(self, temp_dirs):
        """Test fetching a single card using simple format."""
        front_dir, double_sided_dir = temp_dirs

        # Use a very small decklist - just 1 card
        deck_text = "Lightning Bolt"

        handle_card = get_handle_card(
            ignore_set_and_collector_number=False,
            prefer_older_sets=False,
            prefer_sets=[],
            ignore_sets=[],
            prefer_showcase=False,
            prefer_extra_art=False,
            prefer_ub=False,
            ignore_ub=False,
            prefer_langs=None,
            tokens=False,
            front_img_dir=front_dir,
            double_sided_dir=double_sided_dir
        )

        parse_deck(deck_text, DeckFormat.SIMPLE, handle_card)

        # Check that at least one image was created
        files = os.listdir(front_dir)
        assert len(files) >= 1

        # Verify image file has content (> 0 bytes)
        for f in files:
            file_path = os.path.join(front_dir, f)
            assert os.path.getsize(file_path) > 0

    def test_fetch_double_faced_card(self, temp_dirs):
        """Test fetching a double-faced card."""
        front_dir, double_sided_dir = temp_dirs

        # Use a modal double-faced card
        deck_text = "1 Agadeem's Awakening // Agadeem, the Undercrypt (ZNR) 90"

        handle_card = get_handle_card(
            ignore_set_and_collector_number=False,
            prefer_older_sets=False,
            prefer_sets=[],
            ignore_sets=[],
            prefer_showcase=False,
            prefer_extra_art=False,
            prefer_ub=False,
            ignore_ub=False,
            prefer_langs=None,
            tokens=False,
            front_img_dir=front_dir,
            double_sided_dir=double_sided_dir
        )

        parse_deck(deck_text, DeckFormat.MTGA, handle_card)

        # Check front side was saved
        front_files = os.listdir(front_dir)
        assert len(front_files) >= 1

        for f in front_files:
            file_path = os.path.join(front_dir, f)
            assert os.path.getsize(file_path) > 0

    def test_fetch_flavor_name_card(self, temp_dirs):
        """Cards with flavor names (e.g. convention promos) resolve to the correct card art."""
        front_dir, double_sided_dir = temp_dirs

        handle_card = get_handle_card(
            ignore_set_and_collector_number=False,
            prefer_older_sets=False,
            prefer_sets=[],
            ignore_sets=[],
            prefer_showcase=False,
            prefer_extra_art=False,
            prefer_ub=False,
            ignore_ub=False,
            prefer_langs=None,
            tokens=False,
            front_img_dir=front_dir,
            double_sided_dir=double_sided_dir
        )

        handle_card(1, "Donnie's Bō", "", "", 1)

        files = os.listdir(front_dir)
        assert len(files) == 1
        assert os.path.getsize(os.path.join(front_dir, files[0])) > 0

    def test_fetch_with_quantity(self, temp_dirs):
        """Test fetching cards with quantity > 1."""
        front_dir, double_sided_dir = temp_dirs

        deck_text = "2 Lightning Bolt"

        handle_card = get_handle_card(
            ignore_set_and_collector_number=False,
            prefer_older_sets=False,
            prefer_sets=[],
            ignore_sets=[],
            prefer_showcase=False,
            prefer_extra_art=False,
            prefer_ub=False,
            ignore_ub=False,
            prefer_langs=None,
            tokens=False,
            front_img_dir=front_dir,
            double_sided_dir=double_sided_dir
        )

        parse_deck(deck_text, DeckFormat.MTGO, handle_card)

        # Should have 2 copies of the card
        files = os.listdir(front_dir)
        assert len(files) == 2

        for f in files:
            file_path = os.path.join(front_dir, f)
            assert os.path.getsize(file_path) > 0

    def test_fetch_reversible_card(self, temp_dirs):
        """Fetching a reversible_card saves both the front and back art."""
        front_dir, double_sided_dir = temp_dirs

        # Anointed Procession (SLD) 1511 is a reversible_card layout — same card name/rules on both
        # sides, but with different artwork. Both faces should be downloaded.
        deck_text = "1 Anointed Procession (SLD) 1511"

        handle_card = get_handle_card(
            ignore_set_and_collector_number=False,
            prefer_older_sets=False,
            prefer_sets=[],
            ignore_sets=[],
            prefer_showcase=False,
            prefer_extra_art=False,
            prefer_ub=False,
            ignore_ub=False,
            prefer_langs=None,
            tokens=False,
            front_img_dir=front_dir,
            double_sided_dir=double_sided_dir
        )

        parse_deck(deck_text, DeckFormat.MTGA, handle_card)

        # Front image should be saved
        front_files = os.listdir(front_dir)
        assert len(front_files) == 1
        assert os.path.getsize(os.path.join(front_dir, front_files[0])) > 0

        # Back image should also be saved
        back_files = os.listdir(double_sided_dir)
        assert len(back_files) == 1
        assert os.path.getsize(os.path.join(double_sided_dir, back_files[0])) > 0

    def test_fetch_meld_card(self, temp_dirs):
        """Fetching a meld part saves its front art and a cropped half of the combined meld result as the back."""
        from PIL import Image
        front_dir, double_sided_dir = temp_dirs

        # Bruna, the Fading Light is a meld part whose back is the top half of Brisela, Voice of Nightmares
        deck_text = "1 Bruna, the Fading Light (EMN) 15"

        handle_card = get_handle_card(
            ignore_set_and_collector_number=False,
            prefer_older_sets=False,
            prefer_sets=[],
            ignore_sets=[],
            prefer_showcase=False,
            prefer_extra_art=False,
            prefer_ub=False,
            ignore_ub=False,
            prefer_langs=None,
            tokens=False,
            front_img_dir=front_dir,
            double_sided_dir=double_sided_dir
        )

        parse_deck(deck_text, DeckFormat.MTGA, handle_card)

        # Front image of Bruna should be saved
        front_files = os.listdir(front_dir)
        assert len(front_files) == 1
        assert os.path.getsize(os.path.join(front_dir, front_files[0])) > 0

        # Cropped meld result (top half of Brisela, resized to full card) should be in double_sided_dir
        back_files = os.listdir(double_sided_dir)
        assert len(back_files) == 1
        back_path = os.path.join(double_sided_dir, back_files[0])
        assert os.path.getsize(back_path) > 0

        # The saved back image should have full card dimensions (same width as the meld result image)
        back_img = Image.open(back_path)
        front_img = Image.open(os.path.join(front_dir, front_files[0]))
        assert back_img.size == front_img.size


@pytest.mark.integration
class TestUniverseBeyondScryfallData:
    """Sanity checks that the Scryfall data for our test cards matches expectations.

    If these fail it means the cards have received new printings that change their
    UB/non-UB composition — update the URIs below and re-check the
    filtering tests, rather than assuming the plugin is broken.

    Oracle IDs verified from stable card IDs:
    - Skrelv: https://api.scryfall.com/cards/509c00d2-6a84-4760-8927-483ed123b05f
    - Excalibur: https://api.scryfall.com/cards/4e357b2d-a3c1-490e-a37c-cdf42abcfa60
    """

    SKRELV_PRINTS_URI = 'https://api.scryfall.com/cards/search?order=released&q=oracleid%3A20053847-6623-493c-8cdb-a69cda3b1577&unique=prints'
    EXCALIBUR_PRINTS_URI = 'https://api.scryfall.com/cards/search?order=released&q=oracleid%3A9fb6bd72-031b-40a1-83c5-8a1c82f84e12&unique=prints'

    def test_skrelv_has_ub_printing(self):
        """Scryfall still lists a UB printing of Skrelv (SLD 1926)."""
        printings = fetch_printings(self.SKRELV_PRINTS_URI, None, 'Skrelv, Defector Mite')
        sets = {p['set'] for p in printings}
        assert 'sld' in sets, (
            "Scryfall no longer lists SLD as a printing of Skrelv. "
            "Update the expected set codes in TestUniverseBeyondFiltering."
        )

    def test_skrelv_has_non_ub_printing(self):
        """Scryfall still lists a non-UB printing of Skrelv (ONE 225)."""
        printings = fetch_printings(self.SKRELV_PRINTS_URI, None, 'Skrelv, Defector Mite')
        sets = {p['set'] for p in printings}
        assert 'one' in sets, (
            "Scryfall no longer lists ONE as a printing of Skrelv. "
            "Update the expected set codes in TestUniverseBeyondFiltering."
        )

    def test_excalibur_is_ub_only(self):
        """Scryfall lists Excalibur only in UB sets — no non-UB printings exist."""
        all_printings = fetch_printings(self.EXCALIBUR_PRINTS_URI, None, 'Excalibur, Sword of Eden')
        non_ub_printings = fetch_printings(self.EXCALIBUR_PRINTS_URI, False, 'Excalibur, Sword of Eden')
        assert len(non_ub_printings) == len(all_printings), (
            "Excalibur now has a non-UB printing. It can no longer be used as the "
            "UB-only fallback test case — update TestUniverseBeyondFiltering."
        )


@pytest.mark.integration
class TestLanguagePrioritization:
    """Unit tests for language prioritization in progressive filtering.

    When prefer_langs is specified, the filtering logic should prioritize language
    BEFORE other aesthetic filters (showcase, extra_art, etc). This ensures users
    get cards in their preferred language even if fancier versions are only available
    in English.
    """

    def make_printing(self, set_code, collector_number, lang='en', full_art=False, showcase=False):
        """Helper to create a mock printing with specified attributes."""
        return {
            'set': set_code,
            'collector_number': collector_number,
            'lang': lang,
            'nonfoil': True,
            'digital': False,
            'promo': False,
            'full_art': full_art,
            'border_color': 'borderless' if full_art else 'black',
            'frame_effects': ['showcase'] if showcase else [],
        }

    @patch('plugins.mtg.scryfall.fetch_card_art')
    @patch('plugins.mtg.scryfall.request_scryfall')
    def test_prefer_german_over_english_full_art(self, mock_request, mock_fetch_art):
        """When a card has English full-art and German normal versions, German is selected."""
        card_json = {
            'name': 'Lightning Bolt',
            'set': 'lea',
            'collector_number': '1',
            'layout': 'normal',
            'prints_search_uri': PRINTS_SEARCH_URI,
        }

        printings = [
            self.make_printing('lea', '1', 'en', full_art=True),   # English full-art
            self.make_printing('lea', '2', 'de', full_art=False),  # German normal
        ]

        named_response = MagicMock()
        named_response.json.return_value = card_json
        printings_response = MagicMock()
        printings_response.json.return_value = {'data': printings}
        mock_request.side_effect = [named_response, printings_response]

        fetch_card(1, 1, "", "", False, "Lightning Bolt",
                   False, [], [], False, True, False, False,
                   [ScryfallLanguage.GERMAN], False,
                   front_img_dir='front', double_sided_dir='double_sided')

        # Should select German printing even though English has full_art
        args, _ = mock_fetch_art.call_args
        assert args[3] == 'lea'
        assert args[4] == '2'  # German version

    @patch('plugins.mtg.scryfall.fetch_card_art')
    @patch('plugins.mtg.scryfall.request_scryfall')
    def test_prefer_german_over_english_showcase(self, mock_request, mock_fetch_art):
        """When a card has English showcase and German normal versions, German is selected."""
        card_json = {
            'name': 'Sol Ring',
            'set': 'lea',
            'collector_number': '1',
            'layout': 'normal',
            'prints_search_uri': PRINTS_SEARCH_URI,
        }

        printings = [
            self.make_printing('lea', '1', 'en', showcase=True),   # English showcase
            self.make_printing('lea', '2', 'de', showcase=False),  # German normal
        ]

        named_response = MagicMock()
        named_response.json.return_value = card_json
        printings_response = MagicMock()
        printings_response.json.return_value = {'data': printings}
        mock_request.side_effect = [named_response, printings_response]

        fetch_card(1, 1, "", "", False, "Sol Ring",
                   False, [], [], True, False, False, False,
                   [ScryfallLanguage.GERMAN], False,
                   front_img_dir='front', double_sided_dir='double_sided')

        # Should select German printing even though English has showcase
        args, _ = mock_fetch_art.call_args
        assert args[3] == 'lea'
        assert args[4] == '2'  # German version

    @patch('plugins.mtg.scryfall.fetch_card_art')
    @patch('plugins.mtg.scryfall.request_scryfall')
    def test_prefer_german_showcase_over_german_normal(self, mock_request, mock_fetch_art):
        """When both German showcase and German normal exist, German showcase is selected."""
        card_json = {
            'name': 'Path to Exile',
            'set': 'lea',
            'collector_number': '1',
            'layout': 'normal',
            'prints_search_uri': PRINTS_SEARCH_URI,
        }

        printings = [
            self.make_printing('lea', '1', 'en', showcase=True),   # English showcase
            self.make_printing('lea', '2', 'de', showcase=False),  # German normal
            self.make_printing('lea', '3', 'de', showcase=True),   # German showcase
        ]

        named_response = MagicMock()
        named_response.json.return_value = card_json
        printings_response = MagicMock()
        printings_response.json.return_value = {'data': printings}
        mock_request.side_effect = [named_response, printings_response]

        fetch_card(1, 1, "", "", False, "Path to Exile",
                   False, [], [], True, False, False, False,
                   [ScryfallLanguage.GERMAN], False,
                   front_img_dir='front', double_sided_dir='double_sided')

        # Should select German showcase over German normal
        args, _ = mock_fetch_art.call_args
        assert args[3] == 'lea'
        assert args[4] == '3'  # German showcase

    @patch('plugins.mtg.scryfall.fetch_card_art')
    @patch('plugins.mtg.scryfall.request_scryfall')
    def test_multiple_prefer_langs_with_priority(self, mock_request, mock_fetch_art):
        """When prefer_langs=[GERMAN, FRENCH], German is preferred over French."""
        card_json = {
            'name': 'Counterspell',
            'set': 'lea',
            'collector_number': '1',
            'layout': 'normal',
            'prints_search_uri': PRINTS_SEARCH_URI,
        }

        printings = [
            self.make_printing('lea', '1', 'en'),  # English
            self.make_printing('lea', '2', 'fr'),  # French
            self.make_printing('lea', '3', 'de'),  # German
        ]

        named_response = MagicMock()
        named_response.json.return_value = card_json
        printings_response = MagicMock()
        printings_response.json.return_value = {'data': printings}
        mock_request.side_effect = [named_response, printings_response]

        fetch_card(1, 1, "", "", False, "Counterspell",
                   False, [], [], False, False, False, False,
                   [ScryfallLanguage.GERMAN, ScryfallLanguage.FRENCH], False,
                   front_img_dir='front', double_sided_dir='double_sided')

        # Should select German (first in prefer_langs) over French
        args, _ = mock_fetch_art.call_args
        assert args[3] == 'lea'
        assert args[4] == '3'  # German

    @patch('plugins.mtg.scryfall.fetch_card_art')
    @patch('plugins.mtg.scryfall.request_scryfall')
    def test_fallback_to_english_when_preferred_lang_unavailable(self, mock_request, mock_fetch_art):
        """When preferred language is unavailable, falls back to English."""
        card_json = {
            'name': 'Ancient Tomb',
            'set': 'lea',
            'collector_number': '1',
            'layout': 'normal',
            'prints_search_uri': PRINTS_SEARCH_URI,
        }

        printings = [
            self.make_printing('lea', '1', 'en', full_art=True),  # English full-art (only option)
        ]

        named_response = MagicMock()
        named_response.json.return_value = card_json
        printings_response = MagicMock()
        printings_response.json.return_value = {'data': printings}
        mock_request.side_effect = [named_response, printings_response]

        fetch_card(1, 1, "", "", False, "Ancient Tomb",
                   False, [], [], False, True, False, False,
                   [ScryfallLanguage.GERMAN], False,
                   front_img_dir='front', double_sided_dir='double_sided')

        # Should fall back to English when German is unavailable
        args, _ = mock_fetch_art.call_args
        assert args[3] == 'lea'
        assert args[4] == '1'  # English version


@pytest.mark.integration
class TestUniverseBeyondFiltering:
    """Integration tests for prefer_ub and ignore_ub options via fetch_printings.

    Skrelv, Defector Mite exists as both a standard printing (ONE 225)
    and a Universe Beyond printing (SLD 1926).
    Excalibur, Sword of Eden only exists as a Universe Beyond printing (ACR 72).

    Oracle IDs verified from stable card IDs:
    - Skrelv: https://api.scryfall.com/cards/509c00d2-6a84-4760-8927-483ed123b05f
    - Excalibur: https://api.scryfall.com/cards/4e357b2d-a3c1-490e-a37c-cdf42abcfa60
    """

    SKRELV_PRINTS_URI = 'https://api.scryfall.com/cards/search?order=released&q=oracleid%3A20053847-6623-493c-8cdb-a69cda3b1577&unique=prints'
    EXCALIBUR_PRINTS_URI = 'https://api.scryfall.com/cards/search?order=released&q=oracleid%3A9fb6bd72-031b-40a1-83c5-8a1c82f84e12&unique=prints'

    def test_prefer_ub_returns_only_ub_printings(self):
        """prefer_ub=True returns only Universe Beyond printings of Skrelv."""
        printings = fetch_printings(self.SKRELV_PRINTS_URI, True, 'Skrelv, Defector Mite')

        sets = {p['set'] for p in printings}
        assert 'sld' in sets
        assert 'one' not in sets

    def test_ignore_ub_returns_only_non_ub_printings(self):
        """ignore_ub=True returns only non-Universe Beyond printings of Skrelv."""
        printings = fetch_printings(self.SKRELV_PRINTS_URI, False, 'Skrelv, Defector Mite')

        sets = {p['set'] for p in printings}
        assert 'sld' not in sets
        assert 'one' in sets

    def test_no_filter_returns_all_printings(self):
        """prefer_ub=None returns all printings including both UB and non-UB."""
        printings = fetch_printings(self.SKRELV_PRINTS_URI, None, 'Skrelv, Defector Mite')

        sets = {p['set'] for p in printings}
        assert 'one' in sets
        assert 'sld' in sets

    def test_ignore_ub_falls_back_for_ub_only_card(self):
        """ignore_ub=True falls back to all printings when every printing is UB."""
        printings = fetch_printings(self.EXCALIBUR_PRINTS_URI, False, 'Excalibur, Sword of Eden')

        # Fallback: should still return printings rather than an empty list
        assert len(printings) > 0
        assert any(p['set'] == 'acr' for p in printings)


# --- MPCFill XML ---

# Minimal byte blobs whose magic numbers are enough for guess_extension() to sniff.
PNG_BYTES = b'\x89PNG\r\n\x1a\n' + b'\x00' * 32
JPG_BYTES = b'\xff\xd8\xff\xe0' + b'\x00' * 32


def make_mpcfill_xml(quantity, fronts, backs=None, cardback=None):
    """Build an MPCFill order from (card_id, slots, name) tuples."""
    def cards(entries):
        return ''.join(
            f'<card><id>{card_id}</id><slots>{slots}</slots><name>{name}</name></card>'
            for card_id, slots, name in entries
        )

    xml = f'<order><details><quantity>{quantity}</quantity></details>'
    xml += f'<fronts>{cards(fronts)}</fronts>'
    if backs is not None:
        xml += f'<backs>{cards(backs)}</backs>'
    if cardback is not None:
        xml += f'<cardback>{cardback}</cardback>'
    return xml + '</order>'


class TestMPCFillXmlParsing:
    """Test slot assignment when parsing MPCFill orders."""

    def test_expands_multi_slot_cards_and_uses_one_based_slots(self):
        """A card listed for several slots yields one call per slot, numbered from 1."""
        deck_text = make_mpcfill_xml(3, [
            ('island_id', '0,2', 'Island [DFT].png'),
            ('sol_ring_id', '1', 'Sol Ring.jpg'),
        ])

        parsed_slots = []
        def collect_slot(slot, front_id, front_name, back_id, back_name):
            parsed_slots.append((slot, front_id, front_name, back_id, back_name))

        parse_mpcfill_xml(deck_text, collect_slot)

        assert parsed_slots == [
            (1, 'island_id', 'Island [DFT]', None, None),
            (2, 'sol_ring_id', 'Sol Ring', None, None),
            (3, 'island_id', 'Island [DFT]', None, None),
        ]

    def test_assigns_backs_to_their_slots_only(self):
        """Only slots listed in <backs> get a back; the rest stay None."""
        deck_text = make_mpcfill_xml(
            2,
            [('front_a', '0', 'Alrund.jpg'), ('front_b', '1', 'Sol Ring.jpg')],
            backs=[('back_a', '0', 'Hakka.jpg')],
        )

        parsed_slots = []
        def collect_slot(slot, front_id, front_name, back_id, back_name):
            parsed_slots.append((slot, back_id, back_name))

        parse_mpcfill_xml(deck_text, collect_slot)

        assert parsed_slots == [(1, 'back_a', 'Hakka'), (2, None, None)]

    def test_empty_backs_element_is_not_an_error(self):
        """An empty <backs></backs> parses without relying on Element truthiness."""
        deck_text = make_mpcfill_xml(1, [('front_a', '0', 'Sol Ring.jpg')], backs=[])

        parsed_slots = []
        with warnings.catch_warnings():
            # Element truthiness is deprecated; this must not depend on it.
            warnings.simplefilter('error', DeprecationWarning)
            parse_mpcfill_xml(deck_text, lambda *args: parsed_slots.append(args))

        assert len(parsed_slots) == 1

    def test_missing_fronts_raises(self):
        """An order with no <fronts> is not usable."""
        deck_text = '<order><details><quantity>1</quantity></details></order>'

        with pytest.raises(ValueError):
            parse_mpcfill_xml(deck_text, lambda *args: None)

    def test_skips_slot_with_no_front(self, capsys):
        """A slot no front claims is warned about and skipped."""
        deck_text = make_mpcfill_xml(2, [('front_a', '0', 'Sol Ring.jpg')])

        parsed_slots = []
        parse_mpcfill_xml(deck_text, lambda slot, *args: parsed_slots.append(slot))

        assert parsed_slots == [1]
        assert 'Slot 2 has no front image' in capsys.readouterr().out


class TestMPCFillCardback:
    """Test extraction of the order's deck-wide <cardback>."""

    def test_returns_cardback_id(self):
        deck_text = make_mpcfill_xml(1, [('front_a', '0', 'Sol Ring.jpg')], cardback='lotus_id')

        assert extract_mpcfill_cardback_id(deck_text) == 'lotus_id'

    def test_returns_none_when_absent(self):
        deck_text = make_mpcfill_xml(1, [('front_a', '0', 'Sol Ring.jpg')])

        assert extract_mpcfill_cardback_id(deck_text) is None

    def test_returns_none_when_blank(self):
        """A present but empty <cardback> is treated as absent."""
        deck_text = make_mpcfill_xml(1, [('front_a', '0', 'Sol Ring.jpg')], cardback='   ')

        assert extract_mpcfill_cardback_id(deck_text) is None


class TestWriteImage:
    """Test the extension sniffing and stale-file cleanup in write_image()."""

    def test_sniffs_extension_from_bytes(self, tmp_path):
        path = write_image(str(tmp_path), '1SolRing', JPG_BYTES)

        assert os.path.basename(path) == '1SolRing.jpg'
        assert os.path.exists(path)

    def test_replaces_same_stem_file_from_earlier_run(self, tmp_path):
        """Re-fetching a card whose art changed format must not leave both files.

        create_pdf.py's resolve_image_with_any_extension() fails on an ambiguous
        stem match, so the old extension has to go.
        """
        write_image(str(tmp_path), '1SolRing', JPG_BYTES)
        write_image(str(tmp_path), '1SolRing', PNG_BYTES)

        assert [p.name for p in tmp_path.iterdir()] == ['1SolRing.png']

    def test_leaves_other_stems_alone(self, tmp_path):
        write_image(str(tmp_path), '1SolRing', JPG_BYTES)
        write_image(str(tmp_path), '2SolRing', PNG_BYTES)

        assert sorted(p.name for p in tmp_path.iterdir()) == ['1SolRing.jpg', '2SolRing.png']


class TestMPCFillFetcher:
    """Test that collected slots turn into the right downloads and files."""

    @pytest.fixture
    def dirs(self, tmp_path):
        front, double_sided, back = tmp_path / 'front', tmp_path / 'ds', tmp_path / 'back'
        for d in (front, double_sided, back):
            d.mkdir()
        return front, double_sided, back

    def make_fetcher(self, dirs):
        front, double_sided, back = dirs
        return MPCFillFetcher(str(front), str(double_sided), str(back))

    def test_downloads_each_unique_card_id_once(self, dirs):
        """Duplicate slots of the same card must not each hit the network."""
        fetcher = self.make_fetcher(dirs)
        fetcher.collect_slot(1, 'island_id', 'Island [DFT]', None, None)
        fetcher.collect_slot(2, 'island_id', 'Island [DFT]', None, None)
        fetcher.collect_slot(3, 'sol_ring_id', 'Sol Ring', None, None)

        with patch('plugins.mtg.mpcfill.request_mpcfill', return_value=PNG_BYTES) as mock_request:
            fetcher.download()

        assert sorted(c.args[0] for c in mock_request.call_args_list) == ['island_id', 'sol_ring_id']

    def test_writes_one_front_file_per_slot(self, dirs):
        front, _, _ = dirs
        fetcher = self.make_fetcher(dirs)
        fetcher.collect_slot(1, 'island_id', 'Island [DFT]', None, None)
        fetcher.collect_slot(2, 'island_id', 'Island [DFT]', None, None)

        with patch('plugins.mtg.mpcfill.request_mpcfill', return_value=PNG_BYTES):
            fetcher.download()

        assert sorted(p.name for p in front.iterdir()) == ['1IslandDFT.png', '2IslandDFT.png']

    def test_back_image_uses_front_name(self, dirs):
        """create_pdf.py matches double-sided backs by the front's filename."""
        front, double_sided, _ = dirs
        fetcher = self.make_fetcher(dirs)
        fetcher.collect_slot(1, 'front_id', 'Alrund, God of the Cosmos', 'back_id', 'Hakka, Whispering Raven')

        with patch('plugins.mtg.mpcfill.request_mpcfill', return_value=PNG_BYTES):
            fetcher.download()

        assert [p.name for p in front.iterdir()] == ['1AlrundGodoftheCosmos.png']
        assert [p.name for p in double_sided.iterdir()] == ['1AlrundGodoftheCosmos.png']

    def test_cardback_goes_to_back_directory(self, dirs):
        front, double_sided, back = dirs
        fetcher = self.make_fetcher(dirs)
        fetcher.collect_slot(1, 'front_id', 'Sol Ring', None, None)
        fetcher.collect_cardback('lotus_id')

        with patch('plugins.mtg.mpcfill.request_mpcfill', return_value=JPG_BYTES):
            fetcher.download()

        assert [p.name for p in back.iterdir()] == [f'{CARDBACK_STEM}.jpg']
        assert [p.name for p in double_sided.iterdir()] == []

    def test_one_failed_card_does_not_abort_the_rest(self, dirs, capsys):
        front, _, _ = dirs
        fetcher = self.make_fetcher(dirs)
        fetcher.collect_slot(1, 'good_id', 'Sol Ring', None, None)
        fetcher.collect_slot(2, 'bad_id', 'Mana Crypt', None, None)

        def fake_request(card_id):
            if card_id == 'bad_id':
                raise requests.HTTPError('500 Server Error')
            return PNG_BYTES

        with patch('plugins.mtg.mpcfill.request_mpcfill', side_effect=fake_request):
            fetcher.download()

        assert [p.name for p in front.iterdir()] == ['1SolRing.png']
        output = capsys.readouterr().out
        assert 'slot 2 (Mana Crypt)' in output
        assert '500 Server Error' in output

    def test_empty_response_is_reported_as_missing(self, dirs, capsys):
        front, _, _ = dirs
        fetcher = self.make_fetcher(dirs)
        fetcher.collect_slot(1, 'empty_id', 'Sol Ring', None, None)

        with patch('plugins.mtg.mpcfill.request_mpcfill', return_value=b''):
            fetcher.download()

        assert [p.name for p in front.iterdir()] == []
        assert 'empty image response' in capsys.readouterr().out

    def test_download_without_collected_slots_is_a_noop(self, dirs):
        fetcher = self.make_fetcher(dirs)

        with patch('plugins.mtg.mpcfill.request_mpcfill') as mock_request:
            fetcher.download()

        mock_request.assert_not_called()

    def test_retries_a_transient_failure(self, dirs):
        """The Apps Script intermittently 404s, so a later attempt should succeed."""
        front, _, _ = dirs
        fetcher = self.make_fetcher(dirs)
        fetcher.collect_slot(1, 'flaky_id', 'Portal to Phyrexia', None, None)

        attempts = [requests.HTTPError('404 Client Error'), PNG_BYTES]
        def fake_request(card_id):
            result = attempts.pop(0)
            if isinstance(result, Exception):
                raise result
            return result

        with patch('plugins.mtg.mpcfill.RETRY_DELAY_SECONDS', 0):
            with patch('plugins.mtg.mpcfill.request_mpcfill', side_effect=fake_request):
                fetcher.download()

        assert [p.name for p in front.iterdir()] == ['1PortaltoPhyrexia.png']

    def test_retries_an_empty_response(self, dirs):
        """An empty body is treated as a transient failure, not a real image."""
        front, _, _ = dirs
        fetcher = self.make_fetcher(dirs)
        fetcher.collect_slot(1, 'flaky_id', 'Sol Ring', None, None)

        with patch('plugins.mtg.mpcfill.RETRY_DELAY_SECONDS', 0):
            with patch('plugins.mtg.mpcfill.request_mpcfill', side_effect=[b'', PNG_BYTES]):
                fetcher.download()

        assert [p.name for p in front.iterdir()] == ['1SolRing.png']

    def test_gives_up_after_max_attempts(self, dirs, capsys):
        front, _, _ = dirs
        fetcher = self.make_fetcher(dirs)
        fetcher.collect_slot(1, 'dead_id', 'Sol Ring', None, None)

        error = requests.HTTPError('404 Client Error')
        with patch('plugins.mtg.mpcfill.RETRY_DELAY_SECONDS', 0):
            with patch('plugins.mtg.mpcfill.request_mpcfill', side_effect=error) as mock_request:
                fetcher.download()

        assert mock_request.call_count == 3
        assert [p.name for p in front.iterdir()] == []
        assert '404 Client Error' in capsys.readouterr().out
