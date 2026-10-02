"""
Tests for the Dragon Ball Super Card Game Fusion World plugin.
Tests deck format parsing and image fetching from dbs-cardgame.com.
"""
import os
import shutil
import tempfile
import pytest
from PIL import Image

from plugins.dragon_ball_super_fusion_world.deck_formats import (
    DeckFormat,
    parse_deck,
    parse_fusionworld,
    parse_deckplanet,
)
from plugins.dragon_ball_super_fusion_world import dbs_cardgame
from plugins.dragon_ball_super_fusion_world.dbs_cardgame import (
    card_art_url,
    request_dbs,
    get_handle_card,
)


def collect(deck_text, parse=parse_fusionworld):
    parsed_cards = []
    parse(deck_text, lambda index, card_code, quantity: parsed_cards.append((index, card_code, quantity)))
    return parsed_cards


# --- Unit Tests for Deck Format Parsing ---

class TestFusionWorldFormat:
    """Test Fusion World Digital deck code / Limitless format parsing."""

    def test_parse_quantity_space_code(self):
        deck_text = """1 FB01-001
4 FS01-03
4 FB01-005
3 FS01-04
4 FB01-014"""

        assert collect(deck_text) == [
            (1, 'FB01-001', 1),
            (2, 'FS01-03', 4),
            (3, 'FB01-005', 4),
            (4, 'FS01-04', 3),
            (5, 'FB01-014', 4),
        ]

    def test_parse_x_separators(self):
        deck_text = "4xFB01-005\n2x FB01-014\n3 x FP-001"

        assert collect(deck_text) == [
            (1, 'FB01-005', 4),
            (2, 'FB01-014', 2),
            (3, 'FP-001', 3),
        ]

    def test_parse_trailing_name_and_parallel(self):
        deck_text = "1 FB01-001 Son Goku\n4 FB01-004_p1"

        assert collect(deck_text) == [
            (1, 'FB01-001', 1),
            (2, 'FB01-004_p1', 4),
        ]

    def test_skips_headers_and_blank_lines(self):
        deck_text = "Leader\n1 FB01-001\n\nMain Deck\n4 FS01-03\n"

        assert [c[1] for c in collect(deck_text)] == ['FB01-001', 'FS01-03']

    def test_parse_deck_dispatch(self):
        parsed_cards = []
        parse_deck("2 FB01-005", DeckFormat.FUSIONWORLD, lambda i, c, q: parsed_cards.append((c, q)))
        assert parsed_cards == [('FB01-005', 2)]


class TestDigitalExportFormat:
    """Fusion World Digital / Egman Events / dragonball.gg / DeckPlanet digital exports."""

    def test_parse_egman_export(self):
        # Egman Events getExportText: leader has no quantity and keeps Egman's -F card code suffix
        deck_text = """Name (Exported)
FB01-001-F Son Goku(70)
4 FB01-005 Bulma(75)
4 FS01-03 Master Roshi(5)

Other Cards:
2 FB01-014 Vegeta(84)"""

        assert collect(deck_text) == [
            (1, 'FB01-001-F', 1),
            (2, 'FB01-005', 4),
            (3, 'FS01-03', 4),
            (4, 'FB01-014', 2),
        ]

    def test_parse_dragonballgg_export(self):
        # dragonball.gg textExport: lowercase 'name' header, leader line without quantity
        deck_text = """name (Goku Aggro)
FS01-01 Son Goku(2)
4 FS01-02 Whis(4)
2 FS01-09 Son Gohan : Adolescence(11)"""

        assert collect(deck_text) == [
            (1, 'FS01-01-F', 1),
            (2, 'FS01-02', 4),
            (3, 'FS01-09', 2),
        ]

    def test_parse_deckplanet_digital_and_tcgarena_exports(self):
        digital = "Name (My Deck)\nFB01-001 Son Goku (70)\n4 FB01-005 Bulma (75)"
        tcgarena = "1 FB01-001\n4 FB01-005"

        assert collect(digital) == [(1, 'FB01-001-F', 1), (2, 'FB01-005', 4)]
        assert collect(tcgarena) == [(1, 'FB01-001', 1), (2, 'FB01-005', 4)]


class TestDeckPlanetFormat:
    """DeckPlanet default clipboard export: '{quantity} {name} [{card code}]'."""

    def test_parse_deckplanet(self):
        deck_text = """Son Goku [FB01-001]
4 Son Goku [FB01-005]
2 Son Gohan : Adolescence [FS01-09]
Sideboard
2 Piccolo [FB01-008]"""

        assert collect(deck_text, parse_deckplanet) == [
            (1, 'FB01-001-F', 1),
            (2, 'FB01-005', 4),
            (3, 'FS01-09', 2),
            (4, 'FB01-008', 2),
        ]

    def test_parse_deck_dispatch(self):
        parsed_cards = []
        parse_deck("3 Krillin [FS01-04]", DeckFormat.DECKPLANET, lambda i, c, q: parsed_cards.append((c, q)))
        assert parsed_cards == [('FS01-04', 3)]


class TestLeaderFetch:
    """A -F/-B leader marker skips the plain image probe."""

    def test_marked_leader_requests_only_front_and_back(self, monkeypatch, tmp_path):
        requested = []

        class FakeResponse:
            content = b'img'

        def fake_request(url):
            requested.append(url)
            return FakeResponse()

        monkeypatch.setattr(dbs_cardgame, 'request_dbs', fake_request)
        monkeypatch.setattr(dbs_cardgame, 'guess_extension', lambda _: '.webp')
        front_dir, back_dir = tmp_path / 'front', tmp_path / 'back'
        front_dir.mkdir()
        back_dir.mkdir()

        dbs_cardgame.fetch_card_art(1, 'FB01-001-F', 1, str(front_dir), str(back_dir))

        assert [u.rsplit('/', 1)[1] for u in requested] == ['FB01-001_f.webp', 'FB01-001_b.webp']
        assert os.listdir(front_dir) == ['1FB01-0011.webp']
        assert os.listdir(back_dir) == ['1FB01-0011.webp']


class TestCardArtUrl:
    """Test URL construction for regular, leader, and parallel cards."""

    def test_urls(self):
        base = 'https://www.dbs-cardgame.com/fw/images/cards/card/en/'
        assert card_art_url('FB01-005') == base + 'FB01-005.webp'
        assert card_art_url('FB01-004_p1') == base + 'FB01-004_p1.webp'
        assert card_art_url('FB01-001', '_f') == base + 'FB01-001_f.webp'
        assert card_art_url('FB01-001_p1', '_b') == base + 'FB01-001_b_p1.webp'


# --- Integration Tests for API and Image Fetching ---

@pytest.mark.integration
class TestDragonBallSuperAPI:
    """Test the Dragon Ball Super Fusion World card image server."""

    def test_api_availability(self):
        response = request_dbs(card_art_url('FB01-005'))
        assert response.status_code == 200


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

    def test_fetch_regular_card_with_quantity(self, temp_dirs):
        front_dir, double_sided_dir = temp_dirs

        parse_deck("2 FB01-005", DeckFormat.FUSIONWORLD, get_handle_card(front_dir, double_sided_dir))

        files = sorted(os.listdir(front_dir))
        assert files == ['1FB01-0051.webp', '1FB01-0052.webp']
        assert os.listdir(double_sided_dir) == []
        for f in files:
            with Image.open(os.path.join(front_dir, f)) as img:
                img.verify()

    def test_fetch_leader_is_double_sided(self, temp_dirs):
        front_dir, double_sided_dir = temp_dirs

        parse_deck("1 FB01-001", DeckFormat.FUSIONWORLD, get_handle_card(front_dir, double_sided_dir))

        assert os.listdir(front_dir) == ['1FB01-0011.webp']
        assert os.listdir(double_sided_dir) == ['1FB01-0011.webp']
        with Image.open(os.path.join(double_sided_dir, '1FB01-0011.webp')) as img:
            img.verify()

    def test_fetch_marked_leader_from_digital_export(self, temp_dirs):
        front_dir, double_sided_dir = temp_dirs

        parse_deck("Name (Exported)\nFB01-001 Son Goku(70)",DeckFormat.FUSIONWORLD, get_handle_card(front_dir, double_sided_dir))

        assert os.listdir(front_dir) == ['1FB01-0011.webp']
        assert os.listdir(double_sided_dir) == ['1FB01-0011.webp']
