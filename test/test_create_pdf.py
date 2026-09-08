"""
Tests for create_pdf.py CLI.

Smoke test verifies the CLI runs end-to-end on local fixtures.
Output image tests render pages to PNG and do pixel-level comparison
against pre-generated expected images (see test/generate_expected_images.py).
"""
import os
import tempfile
import pytest
from click.testing import CliRunner
import numpy as np
from PIL import Image, ImageChops
from create_pdf import cli
from pdf_cases import IMAGES_DIR, BACK_DIR, DS_DIR, EXPECTED_DIR, TEST_CASES


# --- Smoke Test ---

def test_basic_create_pdf():
    """Verify the CLI runs without error and produces a PDF."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as output_dir:
        output_path = os.path.join(output_dir, 'game.pdf')
        result = runner.invoke(cli, [
            '--front_dir_path', 'test/basic/front',
            '--back_dir_path', 'test/basic/back',
            '--double_sided_dir_path', DS_DIR,
            '--output_path', output_path,
        ])
        assert result.exit_code == 0
        assert os.path.exists(output_path)


# --- Output Image Tests ---
# These tests invoke the CLI with --output_images, rendering each PDF page to
# PNG, then compare pixel-by-pixel against the expected images in EXPECTED_DIR.

def assert_images_match(actual_dir, expected_dir, max_diff_fraction=0.005):
    """Compare all PNG files in actual_dir against expected_dir pixel-by-pixel.

    max_diff_fraction: fraction of pixels allowed to differ (default 0.5%).
    A small tolerance is needed because JPEG decompression and image resampling
    can produce slightly different pixel values across platforms (e.g. Windows
    vs Linux libjpeg), even when the layout logic is identical.
    """
    actual_files = sorted(f for f in os.listdir(actual_dir) if f.endswith('.png'))
    expected_files = sorted(f for f in os.listdir(expected_dir) if f.endswith('.png'))

    assert actual_files == expected_files, (
        f"File mismatch.\n  Actual: {actual_files}\n  Expected: {expected_files}"
    )

    for filename in actual_files:
        with Image.open(os.path.join(actual_dir, filename)) as actual_img, \
             Image.open(os.path.join(expected_dir, filename)) as expected_img:

            assert actual_img.size == expected_img.size, (
                f"{filename}: size mismatch {actual_img.size} != {expected_img.size}"
            )

            # Convert both to same mode for comparison
            actual_rgb = actual_img.convert('RGB')
            expected_rgb = expected_img.convert('RGB')

        diff = ImageChops.difference(actual_rgb, expected_rgb)
        if diff.getbbox() is not None:
            # Calculate how many pixels differ (any channel non-zero)
            diff_pixels = int(np.any(np.array(diff) != 0, axis=2).sum())
            total_pixels = actual_rgb.size[0] * actual_rgb.size[1]
            diff_fraction = diff_pixels / total_pixels
            if diff_fraction > max_diff_fraction:
                raise AssertionError(
                    f"{filename}: images differ. "
                    f"{diff_pixels}/{total_pixels} pixels differ "
                    f"({diff_fraction:.2%} > {max_diff_fraction:.2%} tolerance)."
                )


def run_output_images_test(test_name, extra_args=None):
    """Helper to run a create_pdf --output_images test case."""
    runner = CliRunner()
    expected_dir = os.path.join(EXPECTED_DIR, test_name)

    assert os.path.isdir(expected_dir), (
        f"Expected images directory not found: {expected_dir}. "
        f"Run 'python test/generate_expected_images.py' first."
    )

    with tempfile.TemporaryDirectory() as output_dir:
        args = [
            '--front_dir_path', IMAGES_DIR,
            '--back_dir_path', BACK_DIR,
            '--double_sided_dir_path', DS_DIR,
            '--output_path', os.path.join(output_dir, 'output.pdf'),
            '--output_images',
        ]
        if extra_args:
            args += extra_args

        result = runner.invoke(cli, args)
        assert result.exit_code == 0, (
            f"CLI failed with exit code {result.exit_code}.\n"
            f"Output: {result.output}\n"
            f"Exception: {result.exception}"
        )

        assert_images_match(output_dir, expected_dir)


@pytest.mark.parametrize("test_name,extra_args", TEST_CASES, ids=[n for n, _ in TEST_CASES])
def test_output_images(test_name, extra_args):
    run_output_images_test(test_name, extra_args)


# --- Borderless Tests ---

def test_borderless_create_pdf():
    """Verify the CLI runs with --borderless and produces a PDF."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as output_dir:
        output_path = os.path.join(output_dir, 'game.pdf')
        result = runner.invoke(cli, [
            '--front_dir_path', 'test/basic/front',
            '--back_dir_path', 'test/basic/back',
            '--double_sided_dir_path', DS_DIR,
            '--output_path', output_path,
            '--borderless',
        ])
        assert result.exit_code == 0, f"CLI failed: {result.output}\n{result.exception}"
        assert os.path.exists(output_path)


def test_borderless_a4_create_pdf():
    """Verify --borderless works with explicit paper size."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as output_dir:
        output_path = os.path.join(output_dir, 'game.pdf')
        result = runner.invoke(cli, [
            '--front_dir_path', 'test/basic/front',
            '--back_dir_path', 'test/basic/back',
            '--double_sided_dir_path', DS_DIR,
            '--output_path', output_path,
            '--borderless',
            '--paper_size', 'a4',
        ])
        assert result.exit_code == 0, f"CLI failed: {result.output}\n{result.exception}"
        assert os.path.exists(output_path)


def test_borderless_with_specialty_errors():
    """--borderless with --specialty should raise an error."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as output_dir:
        output_path = os.path.join(output_dir, 'game.pdf')
        result = runner.invoke(cli, [
            '--front_dir_path', 'test/basic/front',
            '--back_dir_path', 'test/basic/back',
            '--output_path', output_path,
            '--borderless',
            '--specialty', 'letter-commander',
        ])
        assert result.exit_code != 0


# --- Transparent Background Tests ---
# Pages always have a transparent background (see page_manager.generate_reg_mark).

def test_output_images_default_to_png_with_transparent_background():
    """Bare --output_images defaults to png and produces RGBA images with a
    transparent margin and opaque card art."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as output_dir:
        result = runner.invoke(cli, [
            '--front_dir_path', 'test/basic/front',
            '--back_dir_path', 'test/basic/back',
            '--output_path', output_dir,
            '--only_fronts',
            '--output_images',
        ])
        assert result.exit_code == 0, f"CLI failed: {result.output}\n{result.exception}"

        page_path = os.path.join(output_dir, 'page1.png')
        assert os.path.exists(page_path)

        with Image.open(page_path) as img:
            assert img.mode == 'RGBA'
            assert img.getpixel((0, 0))[3] == 0  # page corner is transparent


def test_output_images_with_explicit_format():
    """--output_images accepts an explicit format, e.g. '--output_images webp'."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as output_dir:
        result = runner.invoke(cli, [
            '--front_dir_path', 'test/basic/front',
            '--back_dir_path', 'test/basic/back',
            '--output_path', output_dir,
            '--only_fronts',
            '--output_images', 'webp',
        ])
        assert result.exit_code == 0, f"CLI failed: {result.output}\n{result.exception}"

        page_path = os.path.join(output_dir, 'page1.webp')
        assert os.path.exists(page_path)

        with Image.open(page_path) as img:
            assert img.mode == 'RGBA'


def test_output_images_rejects_alpha_incompatible_format():
    """--output_images only offers formats that can carry the transparent background."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as output_dir:
        result = runner.invoke(cli, [
            '--front_dir_path', 'test/basic/front',
            '--back_dir_path', 'test/basic/back',
            '--output_path', output_dir,
            '--only_fronts',
            '--output_images', 'jpg',
        ])
        assert result.exit_code != 0


def test_pdf_has_transparent_background():
    """Without --output_images, the PDF itself carries real transparency
    (JPEG2000 + SMask), not a flattened white background."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as output_dir:
        output_path = os.path.join(output_dir, 'game.pdf')
        result = runner.invoke(cli, [
            '--front_dir_path', 'test/basic/front',
            '--back_dir_path', 'test/basic/back',
            '--output_path', output_path,
            '--only_fronts',
        ])
        assert result.exit_code == 0, f"CLI failed: {result.output}\n{result.exception}"

        with open(output_path, 'rb') as f:
            pdf_bytes = f.read()
        assert b'JPXDecode' in pdf_bytes
        assert b'SMaskInData' in pdf_bytes
