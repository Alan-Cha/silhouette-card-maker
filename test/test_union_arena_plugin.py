"""
Tests for the Union Arena plugin.
Tests deck format parsing and image fetching from the official card list.
"""
import os
import shutil
import tempfile
import pytest
from PIL import Image

from plugins.union_arena.deck_formats import DeckFormat, parse_deck, parse_exburst, parse_text
from plugins.union_arena.union_arena import CARD_ART_URL_TEMPLATE, card_image_id, card_regions, request_bandai, get_handle_card


# Real ExBurst export ("Beatrice & Subaru", public deck on exburst.dev/ua/en)
EXBURST_DECK = """4 x UE24BT/REZ-1-068
4 x UE24BT/REZ-1-069
4 x UE24BT/REZ-1-070
4 x UE24BT/REZ-1-071
4 x UE24BT/REZ-1-072
4 x UE24BT/REZ-1-073
3 x UE24BT/REZ-1-074
4 x UE24BT/REZ-1-076
3 x UE24BT/REZ-1-077
4 x UE24BT/REZ-1-078
3 x UE24BT/REZ-1-094
4 x UE24BT/REZ-1-095
4 x UE24BT/REZ-1-096
3 x UE24BT/REZ-1-AP05
1 x UE24BT/REZ-1-077-ALT1"""


def collect(parser, deck_text):
    parsed_cards = []
    parser(deck_text, lambda index, card_number, quantity: parsed_cards.append((index, card_number, quantity)))
    return parsed_cards


# --- Unit Tests for Deck Format Parsing ---

class TestExburstFormat:
    """Test ExBurst format parsing."""

    def test_parse_exburst(self):
        deck_text = """4 x UE03BT/JJK-1-001
2 x UEX02BT/JJK-2-045
1 x UE03BT/JJK-1-005_p1"""

        assert collect(parse_exburst, deck_text) == [
            (1, 'UE03BT/JJK-1-001', 4),
            (2, 'UEX02BT/JJK-2-045', 2),
            (3, 'UE03BT/JJK-1-005_p1', 1),
        ]

    def test_parse_real_export(self):
        parsed_cards = collect(parse_exburst, EXBURST_DECK)
        assert len(parsed_cards) == 15
        assert sum(quantity for _, _, quantity in parsed_cards) == 53
        assert parsed_cards[13] == (14, 'UE24BT/REZ-1-AP05', 3)
        assert parsed_cards[14] == (15, 'UE24BT/REZ-1-077-ALT1', 1)

    def test_promo_numbers(self):
        # Real promo numbers from the official NA and JP card lists
        deck_text = """1 x UEPR/JJK-1-001
1 x UEPR/2024-AP02
1 x UEPR/NIK-AP03_p1
1 x UE01ST/BLC-1-AP01_p1
1 x UAPR/IMS_AP04
1 x UAPB/GIM-1-001"""

        assert [card for _, card, _ in collect(parse_exburst, deck_text)] == [
            'UEPR/JJK-1-001', 'UEPR/2024-AP02', 'UEPR/NIK-AP03_p1', 'UE01ST/BLC-1-AP01_p1', 'UAPR/IMS_AP04', 'UAPB/GIM-1-001',
        ]

    def test_short_number_reports_error(self, capsys):
        # Short numbers are parsed (not skipped) so the missing set prefix is reported
        parse_exburst('4 x JJK-1-001', lambda index, card_number, quantity: card_image_id(card_number))
        assert 'missing its set prefix' in capsys.readouterr().out

    def test_skips_non_card_lines(self):
        deck_text = """Main Deck
4 x UE03BT/JJK-1-001

4 UE03BT/JJK-1-002"""

        assert collect(parse_exburst, deck_text) == [(1, 'UE03BT/JJK-1-001', 4)]


class TestTextFormat:
    """Test plain text format parsing."""

    def test_parse_text(self):
        deck_text = """4 UE03BT/JJK-1-001 Yuji Itadori
3 UE03BT/JJK-1-002"""

        assert collect(parse_text, deck_text) == [
            (1, 'UE03BT/JJK-1-001', 4),
            (2, 'UE03BT/JJK-1-002', 3),
        ]


class TestParseDeck:
    def test_dispatch(self):
        assert collect(lambda t, h: parse_deck(t, DeckFormat.EXBURST, h), '4 x UE03BT/JJK-1-001') == [(1, 'UE03BT/JJK-1-001', 4)]
        assert collect(lambda t, h: parse_deck(t, DeckFormat.TEXT, h), '4 UE03BT/JJK-1-001') == [(1, 'UE03BT/JJK-1-001', 4)]

    def test_card_image_id(self):
        assert card_image_id('UE03BT/JJK-1-005_p1') == 'UE03BT_JJK-1-005_p1'
        assert card_image_id('UE01BT/BLC-1-041-ALT3') == 'UE01BT_BLC-1-041_p3'
        assert card_image_id('UAPR/IMS_AP04') == 'UAPR_IMS_AP04'
        with pytest.raises(ValueError, match='UE03BT/JJK-1-001'):
            card_image_id('JJK-1-001')

    def test_card_regions(self):
        assert card_regions('UE03BT_JJK-1-001') == ('na',)
        assert card_regions('UA53BT_CSM-1-001') == ('en', 'jp')


# --- Integration Tests for API and Image Fetching ---

@pytest.mark.integration
class TestUnionArenaAPI:
    """Test the official Union Arena card image server."""

    def test_image_availability(self):
        response = request_bandai(CARD_ART_URL_TEMPLATE.format(region='na', image_id='UE03BT_JJK-1-001'))
        assert response.status_code == 200
        assert response.headers['content-type'].startswith('image/')


@pytest.mark.integration
class TestFullFetchWorkflow:
    """Integration tests for the complete card fetching workflow."""

    @pytest.fixture
    def front_dir(self):
        front_dir = tempfile.mkdtemp()
        yield front_dir
        shutil.rmtree(front_dir)

    def test_fetch_with_quantity(self, front_dir):
        parse_deck('2 x UE03BT/JJK-1-001', DeckFormat.EXBURST, get_handle_card(front_dir))

        files = sorted(os.listdir(front_dir))
        assert files == ['1UE03BT_JJK-1-0011.png', '1UE03BT_JJK-1-0012.png']
        for f in files:
            with Image.open(os.path.join(front_dir, f)) as image:
                image.verify()

    def test_fetch_alt_asia_and_promo(self, front_dir):
        # ExBurst alt art (NA), Asia English card, JP-only Asia promo (falls back from 'en' to 'jp')
        parse_deck("""1 x UE24BT/REZ-1-077-ALT1
1 x UA53BT/CSM-1-001
1 x UAPR/2023-AP01""", DeckFormat.EXBURST, get_handle_card(front_dir))

        assert sorted(os.listdir(front_dir)) == ['1UE24BT_REZ-1-077_p11.png', '2UA53BT_CSM-1-0011.png', '3UAPR_2023-AP011.png']
