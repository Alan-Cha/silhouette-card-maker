"""
Tests for the Legend of the Five Rings: The Card Game plugin.
Tests deck format parsing and image fetching from EmeraldDB.
"""
import json
import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from plugins.legend_of_the_five_rings_lcg import emeralddb
from plugins.legend_of_the_five_rings_lcg.deck_formats import DeckFormat, DECK_URL_PATTERN, parse_deck
from plugins.legend_of_the_five_rings_lcg.emeralddb import fetch_decklist, get_handle_card, pick_version


# Trimmed from a real https://www.emeralddb.org/api/decklists/{id} response
DECKLIST_JSON = json.dumps({
    "id": "75ffc2ba-93a2-4551-bab3-2bb12ce015d7",
    "format": "emerald",
    "name": "Intento 1",
    "primary_clan": "crab",
    "secondary_clan": "phoenix",
    "cards": {
        "fortress-at-the-sea-of-fire": 1,
        "keeper-of-earth": 1,
        "fine-katana": 3,
        "kuni-juurou": 3,
    },
    "card_pack_ids": {
        "fine-katana": "emerald-core-set",
        "kuni-juurou": "ancient-secrets",
    },
})

# Trimmed from a real https://www.emeralddb.org/api/cards entry
A_LEGION_OF_ONE = {
    "id": "a-legion-of-one",
    "name": "A Legion of One",
    "versions": [
        {
            "pack_id": "meditations-on-the-ephemeral",
            "image_url": "http://lcg-cdn.fantasyflightgames.com/l5r/L5C07_116.jpg",
            "rotated": True,
        },
        {
            "pack_id": "emerald-core-set",
            "image_url": "https://emerald-legacy.github.io/emeralddb-images/emerald-core-set/ecs109.webp",
            "rotated": False,
        },
    ],
}


def collect(seen):
    return lambda index, card_id, quantity, pack_id: seen.append((index, card_id, quantity, pack_id))


# --- Unit Tests ---

class TestDeckFormatEnum:
    def test_format_values(self):
        assert DeckFormat.EMERALDDB_JSON.value == 'emeralddb_json'
        assert DeckFormat.EMERALDDB_URL.value == 'emeralddb_url'


class TestDeckURLPattern:
    def test_deck_url_matches(self):
        match = DECK_URL_PATTERN.match("https://www.emeralddb.org/decks/75ffc2ba-93a2-4551-bab3-2bb12ce015d7")
        assert match.group(1) == "75ffc2ba-93a2-4551-bab3-2bb12ce015d7"

    def test_legacy_view_suffix_and_bare_domain_match(self):
        assert DECK_URL_PATTERN.match("https://emeralddb.org/decks/75ffc2ba-93a2-4551-bab3-2bb12ce015d7/view")

    def test_rejects_invalid_urls(self):
        assert not DECK_URL_PATTERN.match("")
        assert not DECK_URL_PATTERN.match("75ffc2ba-93a2-4551-bab3-2bb12ce015d7")
        assert not DECK_URL_PATTERN.match("https://www.emeralddb.org/card/fine-katana")
        assert not DECK_URL_PATTERN.match("https://example.com/decks/75ffc2ba-93a2-4551-bab3-2bb12ce015d7")


class TestParseEmeralddbJson:
    def test_all_cards_handled_with_pack_ids(self):
        seen = []
        parse_deck(DECKLIST_JSON, DeckFormat.EMERALDDB_JSON, collect(seen))

        assert seen == [
            (1, "fortress-at-the-sea-of-fire", 1, None),
            (2, "keeper-of-earth", 1, None),
            (3, "fine-katana", 3, "emerald-core-set"),
            (4, "kuni-juurou", 3, "ancient-secrets"),
        ]

    def test_zero_quantity_is_skipped(self, capsys):
        seen = []
        parse_deck(json.dumps({"cards": {"fine-katana": 0, "kuni-juurou": 2}}), DeckFormat.EMERALDDB_JSON, collect(seen))

        assert seen == [(1, "kuni-juurou", 2, None)]
        assert 'Skipping: "fine-katana"' in capsys.readouterr().out

    def test_errors_are_collected_not_raised(self, capsys):
        def failing(index, card_id, quantity, pack_id):
            raise ValueError("boom")

        parse_deck(DECKLIST_JSON, DeckFormat.EMERALDDB_JSON, failing)
        assert "Errors:" in capsys.readouterr().out

    def test_unrecognized_format_raises(self):
        with pytest.raises(ValueError):
            parse_deck("{}", "not_a_real_format", lambda *args: None)


class TestParseEmeralddbUrl:
    def test_url_fetches_decklist_by_id(self):
        seen = []
        with patch("plugins.legend_of_the_five_rings_lcg.deck_formats.fetch_decklist", return_value=json.loads(DECKLIST_JSON)) as mock_fetch:
            parse_deck("https://www.emeralddb.org/decks/75ffc2ba-93a2-4551-bab3-2bb12ce015d7\n", DeckFormat.EMERALDDB_URL, collect(seen))

        mock_fetch.assert_called_once_with("75ffc2ba-93a2-4551-bab3-2bb12ce015d7")
        assert len(seen) == 4

    def test_url_file_with_bom(self, tmp_path):
        deck_file = tmp_path / "deck.txt"
        deck_file.write_text("https://www.emeralddb.org/decks/75ffc2ba-93a2-4551-bab3-2bb12ce015d7", encoding="utf-8-sig")

        with patch("plugins.legend_of_the_five_rings_lcg.deck_formats.fetch_decklist", return_value={"cards": {}}) as mock_fetch:
            parse_deck(str(deck_file), DeckFormat.EMERALDDB_URL, collect([]))

        mock_fetch.assert_called_once()

    def test_invalid_url_does_not_fetch(self, capsys):
        with patch("plugins.legend_of_the_five_rings_lcg.deck_formats.fetch_decklist") as mock_fetch:
            parse_deck("https://example.com/deck", DeckFormat.EMERALDDB_URL, collect([]))

        mock_fetch.assert_not_called()
        assert "not a valid EmeraldDB deck URL" in capsys.readouterr().out


class TestPickVersion:
    def test_prefers_decklist_pack(self):
        assert pick_version(A_LEGION_OF_ONE, "meditations-on-the-ephemeral")["pack_id"] == "meditations-on-the-ephemeral"

    def test_falls_back_to_non_rotated_printing(self):
        assert pick_version(A_LEGION_OF_ONE)["pack_id"] == "emerald-core-set"

    def test_no_image_raises(self):
        with pytest.raises(ValueError):
            pick_version({"id": "x", "versions": [{"pack_id": "core", "image_url": None}]})


class TestFetchCardArt:
    def test_rejects_non_image_response(self, tmp_path):
        response = MagicMock(headers={"content-type": "text/html"}, content=b"<html></html>")
        with patch.object(emeralddb, "fetch_all_cards", return_value={"a-legion-of-one": A_LEGION_OF_ONE}), \
             patch.object(emeralddb, "request_emeralddb", return_value=response):
            with pytest.raises(ValueError):
                emeralddb.fetch_card_art(1, "a-legion-of-one", 1, str(tmp_path))

        assert list(tmp_path.iterdir()) == []

    def test_unknown_card_raises(self, tmp_path):
        with patch.object(emeralddb, "fetch_all_cards", return_value={}):
            with pytest.raises(ValueError):
                emeralddb.fetch_card_art(1, "not-a-card", 1, str(tmp_path))


# --- Integration Tests ---

@pytest.mark.integration
class TestEmeraldDBAPI:
    def test_decklist_availability(self):
        deck = fetch_decklist("75ffc2ba-93a2-4551-bab3-2bb12ce015d7")
        assert deck["cards"]["fortress-at-the-sea-of-fire"] == 1


@pytest.mark.integration
class TestFullFetchWorkflow:
    @pytest.fixture
    def front_dir(self):
        front_dir = tempfile.mkdtemp()
        yield front_dir
        shutil.rmtree(front_dir)

    def test_fetch_stronghold_and_conflict_card(self, front_dir):
        deck_text = json.dumps({"cards": {"fortress-at-the-sea-of-fire": 1, "a-bad-death": 2}})

        parse_deck(deck_text, DeckFormat.EMERALDDB_JSON, get_handle_card(front_dir))

        files = sorted(os.listdir(front_dir))
        assert files == ["1FortressattheSeaofFire1.webp", "2ABadDeath1.webp", "2ABadDeath2.webp"]

        for f in files:
            with Image.open(os.path.join(front_dir, f)) as img:
                assert img.height > img.width
