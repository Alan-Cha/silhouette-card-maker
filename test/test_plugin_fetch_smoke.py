"""
Smoke tests for plugin fetch.py CLI scripts.

These tests verify that all plugin fetch scripts can be imported and invoked
without import errors. They use empty or minimal decklists to avoid requiring
network access.
"""
import os
import glob
import importlib
import tempfile
import pytest
from click.testing import CliRunner


# List of all plugins with their fetch modules and supported formats
PLUGINS = [
    ('altered', 'plugins.altered.fetch', ['ajordat']),
    ('arkham_horror_lcg', 'plugins.arkham_horror_lcg.fetch', ['arkhamdb_json']),
    ('ashes_reborn', 'plugins.ashes_reborn.fetch', ['ashes']),
    ('bushiroad', 'plugins.bushiroad.fetch', ['bushiroad']),
    ('digimon', 'plugins.digimon.fetch', ['digimon']),
    ('echoes_of_astra', 'plugins.echoes_of_astra.fetch', ['astra_url']),
    ('elestrals', 'plugins.elestrals.fetch', ['elestrals']),
    ('final_fantasy', 'plugins.final_fantasy.fetch', ['fftcg']),
    ('flesh_and_blood', 'plugins.flesh_and_blood.fetch', ['fab']),
    ('grand_archive', 'plugins.grand_archive.fetch', ['gatcg']),
    ('gundam', 'plugins.gundam.fetch', ['gundam']),
    ('keyforge', 'plugins.keyforge.fetch', ['archon_arcana']),
    ('lorcana', 'plugins.lorcana.fetch', ['lorcast']),
    ('lotr_lcg', 'plugins.lotr_lcg.fetch', ['ringsdb_url', 'ringsdb_fellowship_url', 'ringsdb_scenario_url', 'hallofbeorn_url']),
    ('mtg', 'plugins.mtg.fetch', ['moxfield', 'archidekt', 'text']),
    ('netrunner', 'plugins.netrunner.fetch', ['netrunnerdb']),
    ('one_piece', 'plugins.one_piece.fetch', ['one_piece']),
    ('pokemon', 'plugins.pokemon.fetch', ['limitless']),
    ('riftbound', 'plugins.riftbound.fetch', ['riftbound']),
    ('sorcery_contested_realm', 'plugins.sorcery_contested_realm.fetch', ['curiosa']),
    ('star_wars_lcg', 'plugins.star_wars_lcg.fetch', ['swlcgdb_url']),
    ('star_wars_unlimited', 'plugins.star_wars_unlimited.fetch', ['swudb']),
    ('yugioh', 'plugins.yugioh.fetch', ['ydk']),
]


@pytest.mark.parametrize("plugin_name,module_path,formats", PLUGINS, ids=[p[0] for p in PLUGINS])
def test_plugin_fetch_import(plugin_name, module_path, formats):
    """Test that plugin fetch module can be imported without errors."""
    try:
        # Import the module
        module = importlib.import_module(module_path)

        # Verify the CLI function exists
        assert hasattr(module, 'cli'), f"{module_path} should have a 'cli' function"

    except ImportError as e:
        pytest.fail(f"Failed to import {module_path}: {e}")


@pytest.mark.parametrize("plugin_name,module_path,formats", PLUGINS, ids=[p[0] for p in PLUGINS])
def test_plugin_fetch_cli_invocation(plugin_name, module_path, formats):
    """Test that plugin fetch CLI can be invoked with an empty decklist."""
    try:
        module = importlib.import_module(module_path)
        cli = module.cli

        runner = CliRunner()

        # Create a temporary empty decklist file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("")  # Empty decklist
            temp_file = f.name

        try:
            # Try to invoke the CLI with the empty decklist
            # We expect this to either succeed (if empty is valid) or fail gracefully
            # The key is that there should be no import errors
            result = runner.invoke(cli, [temp_file, formats[0]])

            # We don't care if it fails due to empty decklist or missing file
            # We only care that there are no import errors
            # Import errors would show up as AttributeError, ImportError, etc in the exception
            if result.exception:
                # Check that it's not an import-related error
                exception_name = type(result.exception).__name__
                assert exception_name not in ['ImportError', 'ModuleNotFoundError', 'AttributeError'], (
                    f"{plugin_name} has import errors: {result.exception}"
                )
        finally:
            # Clean up temp file
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    except (ImportError, ModuleNotFoundError) as e:
        pytest.fail(f"Failed to import {module_path}: {e}")


def test_all_plugins_accounted_for():
    """Verify that all plugin directories with fetch.py are included in tests."""
    # Find all fetch.py files in plugins directory
    fetch_files = glob.glob('plugins/*/fetch.py')
    plugin_dirs = [os.path.basename(os.path.dirname(f)) for f in fetch_files]

    # Get list of plugins in our test
    tested_plugins = [p[0] for p in PLUGINS]

    # Check if any plugins are missing
    missing_plugins = set(plugin_dirs) - set(tested_plugins)

    assert not missing_plugins, (
        f"The following plugins have fetch.py but are not in the smoke tests: {missing_plugins}"
    )
