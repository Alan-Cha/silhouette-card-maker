import json
import math
import os
import tempfile
import pytest
from pathlib import Path
from PIL import Image

import page_manager
import utilities
from utilities import (
    parse_crop_string,
    convertInToCrop,
    get_image_file_paths,
    check_paths_subset,
    resolve_image_with_any_extension,
    calculate_max_print_bleed,
    delete_hidden_files_in_directory,
    get_directory,
    offset_images,
    save_offset,
    load_saved_offset,
    OffsetData,
    get_back_card_image_path,
    crop_and_scale_image,
    draw_card_with_bleed,
    draw_card_layout,
    add_front_back_pages,
    FitMode,
    asset_directory,
    merge_extra_layouts,
    extra_layout_paths,
    find_extra_layout_owner,
    EXTRA_LAYOUTS_ENV,
)
from enums import Orientation, Registration


class TestParseCropString:
    """Tests for parse_crop_string() function."""

    def test_none_returns_zero(self):
        """None input should return (0, 0)."""
        assert parse_crop_string(None, 750, 1050) == (0, 0)

    def test_plain_integer(self):
        """Plain integer string should return same value for both dimensions."""
        assert parse_crop_string("9", 750, 1050) == (9, 9)

    def test_plain_float(self):
        """Plain float string should return same value for both dimensions."""
        assert parse_crop_string("6.5", 750, 1050) == (6.5, 6.5)

    def test_decimal_only(self):
        """Decimal without leading zero should parse correctly."""
        assert parse_crop_string(".5", 750, 1050) == (0.5, 0.5)

    def test_mm_integer(self):
        """Millimeter format with integer should convert correctly."""
        result = parse_crop_string("3mm", 750, 1050)
        # 3mm = 3/25.4 inches; card is 2.5in x 3.5in at 300ppi
        # crop_x = 2 * (3/25.4) / 2.5 * 100, crop_y = 2 * (3/25.4) / 3.5 * 100
        assert result[0] == pytest.approx(600 / 63.5)
        assert result[1] == pytest.approx(600 / 88.9)

    def test_mm_float(self):
        """Millimeter format with float should convert correctly."""
        result = parse_crop_string("2.5mm", 750, 1050)
        # 2.5mm = 2.5/25.4 inches
        assert result[0] == pytest.approx(500 / 63.5)
        assert result[1] == pytest.approx(500 / 88.9)

    def test_inches_format(self):
        """Inch format should convert correctly."""
        result = parse_crop_string("0.125in", 750, 1050)
        # crop_x = 2 * 0.125 / 2.5 * 100 = 10.0
        # crop_y = 2 * 0.125 / 3.5 * 100 = 100/14
        assert result[0] == pytest.approx(10.0)
        assert result[1] == pytest.approx(100 / 14)

    def test_inches_format_no_leading_zero(self):
        """Inch format without leading zero should work."""
        result = parse_crop_string(".1in", 750, 1050)
        # crop_x = 2 * 0.1 / 2.5 * 100 = 8.0
        # crop_y = 2 * 0.1 / 3.5 * 100 = 40/7
        assert result[0] == pytest.approx(8.0)
        assert result[1] == pytest.approx(40 / 7)

    def test_case_insensitive_mm(self):
        """Millimeter format should be case insensitive."""
        result_lower = parse_crop_string("3mm", 750, 1050)
        result_upper = parse_crop_string("3MM", 750, 1050)
        assert result_lower == result_upper

    def test_case_insensitive_in(self):
        """Inch format should be case insensitive."""
        result_lower = parse_crop_string("0.1in", 750, 1050)
        result_upper = parse_crop_string("0.1IN", 750, 1050)
        assert result_lower == result_upper

    def test_whitespace_trimmed(self):
        """Leading/trailing whitespace should be trimmed."""
        assert parse_crop_string("  9  ", 750, 1050) == (9, 9)

    def test_invalid_format_raises(self):
        """Invalid format should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid crop format"):
            parse_crop_string("invalid", 750, 1050)

    def test_invalid_unit_raises(self):
        """Invalid unit should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid crop format"):
            parse_crop_string("3cm", 750, 1050)

    def test_empty_string_raises(self):
        """Empty string should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid crop format"):
            parse_crop_string("", 750, 1050)


class TestConvertInToCrop:
    """Tests for convertInToCrop() function."""

    def test_zero_crop(self):
        """Zero inch crop should return zero percentages."""
        assert convertInToCrop(0, 750, 1050) == (0, 0)

    def test_exact_values(self):
        """Should compute correct percentages for known inputs."""
        # card_width_mm = 750/300 = 2.5in, card_height_mm = 1050/300 = 3.5in
        # crop_x = 2 * 0.125 / 2.5 * 100 = 10.0
        # crop_y = 2 * 0.125 / 3.5 * 100 ≈ 7.1429
        result = convertInToCrop(0.125, 750, 1050)
        assert result[0] == pytest.approx(10.0)
        assert result[1] == pytest.approx(100 / 14)

    def test_x_y_different_for_nonsquare(self):
        """Non-square card should have different x and y crop percentages."""
        result = convertInToCrop(0.1, 750, 1050)
        # Different dimensions should give different percentages
        assert result[0] != result[1]

    def test_square_card_same_crop(self):
        """Square card should have same x and y crop percentages."""
        result = convertInToCrop(0.1, 750, 750)
        assert result[0] == result[1]

    def test_larger_crop_larger_percentage(self):
        """Larger inch crop should produce larger percentage."""
        result_small = convertInToCrop(0.1, 750, 1050)
        result_large = convertInToCrop(0.2, 750, 1050)
        assert result_large[0] > result_small[0]
        assert result_large[1] > result_small[1]


class TestGetImageFilePaths:
    """Tests for get_image_file_paths() function."""

    def test_empty_directory(self):
        """Empty directory should return empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = get_image_file_paths(tmpdir)
            assert result == []

    def test_finds_png_files(self):
        """Should find PNG files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a valid PNG file
            img = Image.new('RGB', (100, 100), color='red')
            img_path = os.path.join(tmpdir, 'test.png')
            img.save(img_path, 'PNG')

            result = get_image_file_paths(tmpdir)
            assert 'test.png' in result

    def test_finds_jpeg_files(self):
        """Should find JPEG files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            img = Image.new('RGB', (100, 100), color='blue')
            img_path = os.path.join(tmpdir, 'test.jpg')
            img.save(img_path, 'JPEG')

            result = get_image_file_paths(tmpdir)
            assert 'test.jpg' in result

    def test_ignores_non_image_files(self):
        """Should ignore non-image files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a text file
            txt_path = os.path.join(tmpdir, 'readme.txt')
            with open(txt_path, 'w') as f:
                f.write('hello')

            result = get_image_file_paths(tmpdir)
            assert 'readme.txt' not in result

    def test_recursive_search(self):
        """Should find images in subdirectories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = os.path.join(tmpdir, 'subdir')
            os.makedirs(subdir)

            img = Image.new('RGB', (100, 100), color='green')
            img_path = os.path.join(subdir, 'nested.png')
            img.save(img_path, 'PNG')

            result = get_image_file_paths(tmpdir)
            assert any('nested.png' in r for r in result)

    def test_returns_relative_paths(self):
        """Should return paths relative to input directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            img = Image.new('RGB', (100, 100), color='red')
            img_path = os.path.join(tmpdir, 'test.png')
            img.save(img_path, 'PNG')

            result = get_image_file_paths(tmpdir)
            # Should not contain the tmpdir path
            assert all(not r.startswith(tmpdir) for r in result)


class TestCheckPathsSubset:
    """Tests for check_paths_subset() function."""

    def test_empty_sets(self):
        """Empty subset should return empty set."""
        assert check_paths_subset(set(), set()) == set()

    def test_all_in_mainset(self):
        """All subset items in mainset should return empty set."""
        subset = {'card1.png', 'card2.jpg'}
        mainset = {'card1.png', 'card2.png', 'card3.png'}
        result = check_paths_subset(subset, mainset)
        assert result == set()

    def test_missing_from_mainset(self):
        """Items not in mainset should be returned."""
        subset = {'card1.png', 'card4.png'}
        mainset = {'card1.png', 'card2.png', 'card3.png'}
        result = check_paths_subset(subset, mainset)
        assert 'card4.png' in result

    def test_ignores_extension(self):
        """Should match by stem, ignoring extension."""
        subset = {'card1.jpg'}
        mainset = {'card1.png'}
        result = check_paths_subset(subset, mainset)
        # card1.jpg should match card1.png by stem
        assert result == set()

    def test_different_extensions_match(self):
        """Different extensions with same stem should match."""
        subset = {'image.jpeg'}
        mainset = {'image.png', 'other.png'}
        result = check_paths_subset(subset, mainset)
        assert result == set()

    def test_with_paths(self):
        """Should work with path-like strings."""
        subset = {'subdir/card1.png'}
        mainset = {'card1.png', 'card2.png'}
        # stem of 'subdir/card1.png' is 'card1'
        result = check_paths_subset(subset, mainset)
        assert result == set()


class TestResolveImageWithAnyExtension:
    """Tests for resolve_image_with_any_extension() function."""

    def test_exact_path_exists(self):
        """Should return exact path if it exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            img = Image.new('RGB', (100, 100), color='red')
            img_path = os.path.join(tmpdir, 'test.png')
            img.save(img_path, 'PNG')

            result = resolve_image_with_any_extension(img_path)
            assert result == img_path

    def test_finds_different_extension(self):
        """Should find file with different extension."""
        with tempfile.TemporaryDirectory() as tmpdir:
            img = Image.new('RGB', (100, 100), color='red')
            img_path = os.path.join(tmpdir, 'test.jpg')
            img.save(img_path, 'JPEG')

            # Request .png but .jpg exists
            query_path = os.path.join(tmpdir, 'test.png')
            result = resolve_image_with_any_extension(query_path)
            assert result == img_path

    def test_missing_file_raises(self):
        """Should raise FileNotFoundError if no match found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            query_path = os.path.join(tmpdir, 'nonexistent.png')
            with pytest.raises(FileNotFoundError, match="Missing image"):
                resolve_image_with_any_extension(query_path)

    def test_ambiguous_match_raises(self):
        """Should raise ValueError if multiple matches found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create two files with same stem but different extensions
            img = Image.new('RGB', (100, 100), color='red')
            img.save(os.path.join(tmpdir, 'test.png'), 'PNG')
            img.save(os.path.join(tmpdir, 'test.jpg'), 'JPEG')

            # Request a non-existent extension to trigger glob search
            query_path = os.path.join(tmpdir, 'test.gif')
            with pytest.raises(ValueError, match="Ambiguous"):
                resolve_image_with_any_extension(query_path)


class TestCalculateMaxPrintBleed:
    """Tests for calculate_max_print_bleed() function."""

    def test_single_card(self):
        """Single card (1x1 layout) should return (0, 0)."""
        result = calculate_max_print_bleed([100], [100], 200, 300)
        assert result == (0, 0)

    def test_two_columns(self):
        """Two columns should calculate horizontal bleed; single row falls back to min_bleed."""
        # Cards at x=100 and x=400, width=200
        # Gap = 400 - 100 - 200 = 100, bleed = 100/2 = 50
        x_pos = [100, 400]
        y_pos = [100]
        result = calculate_max_print_bleed(x_pos, y_pos, 200, 300)
        assert result[0] == 50  # x bleed
        assert result[1] == 0   # y bleed defaults to min_bleed (0)

    def test_two_rows(self):
        """Two rows should calculate vertical bleed; single column falls back to min_bleed."""
        x_pos = [100]
        y_pos = [100, 500]
        # Gap = 500 - 100 - 300 = 100, bleed = 100/2 = 50
        result = calculate_max_print_bleed(x_pos, y_pos, 200, 300)
        assert result[0] == 0   # x bleed defaults to min_bleed (0)
        assert result[1] == 50  # y bleed

    def test_grid_layout(self):
        """Grid layout (2x2) should calculate both bleeds."""
        x_pos = [100, 400]  # gap = 400 - 100 - 200 = 100, bleed = 50
        y_pos = [100, 500]  # gap = 500 - 100 - 300 = 100, bleed = 50
        result = calculate_max_print_bleed(x_pos, y_pos, 200, 300)
        assert result[0] == 50
        assert result[1] == 50

    def test_unsorted_positions(self):
        """Should handle unsorted position lists."""
        x_pos = [400, 100]  # unsorted
        y_pos = [500, 100]  # unsorted
        result = calculate_max_print_bleed(x_pos, y_pos, 200, 300)
        assert result[0] == 50
        assert result[1] == 50

    def test_min_bleed_single_card(self):
        """Single card with min_bleed should return (min_bleed, min_bleed)."""
        result = calculate_max_print_bleed([100], [100], 200, 300, min_bleed=15)
        assert result == (15, 15)

    def test_min_bleed_single_axis(self):
        """Single-axis dimension should use min_bleed as floor."""
        x_pos = [100, 400]
        y_pos = [100]
        result = calculate_max_print_bleed(x_pos, y_pos, 200, 300, min_bleed=15)
        assert result[0] == 50  # computed from gap
        assert result[1] == 15  # single row uses min_bleed

    def test_negative_gap_clamped_to_zero(self):
        """Overlapping cards (negative gap) should clamp bleed to zero."""
        # Cards would overlap: positions closer than card width
        x_pos = [100, 150]  # gap = 150 - 100 - 200 = -150, max(0, -75) = 0
        y_pos = [100]
        result = calculate_max_print_bleed(x_pos, y_pos, 200, 300)
        assert result[0] == 0  # Negative gap clamped to 0
        assert result[1] == 0  # Single row defaults to min_bleed (0)


class TestDeleteHiddenFilesInDirectory:
    """Tests for delete_hidden_files_in_directory() function."""

    def test_empty_path_does_nothing(self):
        """Empty path should not raise."""
        delete_hidden_files_in_directory("")

    def test_removes_ds_store(self):
        """Should remove .DS_Store files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ds_store = os.path.join(tmpdir, '.DS_Store')
            with open(ds_store, 'w') as f:
                f.write('junk')

            delete_hidden_files_in_directory(tmpdir)
            assert not os.path.exists(ds_store)

    def test_removes_thumbs_db(self):
        """Should remove Thumbs.db files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            thumbs = os.path.join(tmpdir, 'Thumbs.db')
            with open(thumbs, 'w') as f:
                f.write('junk')

            delete_hidden_files_in_directory(tmpdir)
            assert not os.path.exists(thumbs)

    def test_removes_desktop_ini(self):
        """Should remove desktop.ini files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            desktop_ini = os.path.join(tmpdir, 'desktop.ini')
            with open(desktop_ini, 'w') as f:
                f.write('junk')

            delete_hidden_files_in_directory(tmpdir)
            assert not os.path.exists(desktop_ini)

    def test_removes_apple_double_files(self):
        """Should remove Apple double files (._prefix)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            apple_double = os.path.join(tmpdir, '._image.png')
            with open(apple_double, 'w') as f:
                f.write('junk')

            delete_hidden_files_in_directory(tmpdir)
            assert not os.path.exists(apple_double)

    def test_preserves_normal_files(self):
        """Should not remove normal files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            normal_file = os.path.join(tmpdir, 'image.png')
            with open(normal_file, 'w') as f:
                f.write('data')

            delete_hidden_files_in_directory(tmpdir)
            assert os.path.exists(normal_file)


class TestGetDirectory:
    """Tests for get_directory() function."""

    def test_directory_path(self):
        """Directory path should return absolute directory path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = get_directory(tmpdir)
            assert result == os.path.abspath(tmpdir)

    def test_file_path(self):
        """File path should return absolute parent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, 'test.txt')
            with open(file_path, 'w') as f:
                f.write('test')

            result = get_directory(file_path)
            assert result == os.path.abspath(tmpdir)


class TestOffsetImages:
    """Tests for offset_images() function."""

    def test_empty_list(self):
        """Empty list should return empty list."""
        result = offset_images([], 10, 10, 300)
        assert result == []

    def test_single_image_no_offset(self):
        """Single image (front page) should not be offset."""
        img = Image.new('RGB', (100, 100), color='red')
        result = offset_images([img], 10, 10, 300)
        assert len(result) == 1
        assert result[0] is img  # Same object, not modified

    def test_alternating_offset(self):
        """Should offset every other image (back pages)."""
        img1 = Image.new('RGB', (100, 100), color='red')
        img3 = Image.new('RGB', (100, 100), color='green')

        # img2 has a white marker pixel at (0, 0) on a black background
        img2 = Image.new('RGB', (100, 100), color='black')
        img2.putpixel((0, 0), (255, 255, 255))

        result = offset_images([img1, img2, img3], 10, 10, 300)
        assert len(result) == 3
        assert result[0] is img1  # Front page unchanged
        assert result[2] is img3  # Front page unchanged
        # Back page: x_offset is negated to compensate for 180° flip, y_offset is unchanged.
        # floor(-10 * 300/300) = -10, floor(10 * 300/300) = 10
        # White pixel moves (0,0) -> (-10, 10) which wraps to (90, 10) in a 100x100 image.
        assert result[1].getpixel((90, 10)) == (255, 255, 255)
        assert result[1].getpixel((0, 0)) == (0, 0, 0)

    def test_ppi_scaling(self):
        """Offset should scale with PPI."""
        img_front = Image.new('RGB', (100, 100), color='red')

        # White marker pixel at (0, 0) on a black background
        img_back_a = Image.new('RGB', (100, 100), color='black')
        img_back_a.putpixel((0, 0), (255, 255, 255))
        img_back_b = Image.new('RGB', (100, 100), color='black')
        img_back_b.putpixel((0, 0), (255, 255, 255))

        # x_offset is negated: floor(-30 * 300/300) = -30 pixels → wraps to 70 in 100px image
        result_300 = offset_images([img_front.copy(), img_back_a], 30, 0, 300)
        # x_offset is negated: floor(-30 * 600/300) = -60 pixels → wraps to 40 in 100px image
        result_600 = offset_images([img_front.copy(), img_back_b], 30, 0, 600)

        assert result_300[1].getpixel((70, 0)) == (255, 255, 255)
        assert result_600[1].getpixel((40, 0)) == (255, 255, 255)

    def test_angle_offset_fillcolor_rgb(self):
        """Rotating an RGB image should fill exposed corners with white."""
        img_front = Image.new('RGB', (100, 100), color='red')
        img_back = Image.new('RGB', (100, 100), color='black')

        result = offset_images([img_front, img_back], 0, 0, 300, angle_offset=15.0)
        assert result[1].mode == 'RGB'
        assert result[1].getpixel((0, 0)) == (255, 255, 255)

    def test_angle_offset_fillcolor_rgba(self):
        """Rotating an RGBA image should fill exposed corners with transparency, not white."""
        img_front = Image.new('RGBA', (100, 100), color=(255, 0, 0, 255))
        img_back = Image.new('RGBA', (100, 100), color=(0, 0, 0, 255))

        result = offset_images([img_front, img_back], 0, 0, 300, angle_offset=15.0)
        assert result[1].mode == 'RGBA'
        assert result[1].getpixel((0, 0)) == (0, 0, 0, 0)


class TestOffsetDataSaveLoad:
    """Tests for save_offset() and load_saved_offset() functions."""

    def test_save_and_load_roundtrip(self):
        """Saved offset should be loadable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Change to temp directory for the test
            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                save_offset(10, 20)
                result = load_saved_offset()
                assert result is not None
                assert result.x_offset == 10
                assert result.y_offset == 20
            finally:
                os.chdir(original_cwd)

    def test_load_nonexistent_returns_none(self):
        """Loading non-existent offset file should return None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                result = load_saved_offset()
                assert result is None
            finally:
                os.chdir(original_cwd)

    def test_save_and_load_with_angle(self):
        """Saved offset with angle should roundtrip correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                save_offset(10, 20, angle_offset=1.5)
                result = load_saved_offset()
                assert result is not None
                assert result.x_offset == 10
                assert result.y_offset == 20
                assert result.angle_offset == 1.5
            finally:
                os.chdir(original_cwd)

    def test_offset_data_model(self):
        """OffsetData model should work correctly."""
        data = OffsetData(x_offset=5, y_offset=15)
        assert data.x_offset == 5
        assert data.y_offset == 15

    def test_offset_data_default_angle(self):
        """OffsetData should default angle_offset to 0.0."""
        data = OffsetData(x_offset=5, y_offset=15)
        assert data.angle_offset == 0.0

    def test_offset_data_with_angle(self):
        """OffsetData should store angle_offset."""
        data = OffsetData(x_offset=5, y_offset=15, angle_offset=2.5)
        assert data.angle_offset == 2.5


class TestGetBackCardImagePath:
    """Tests for get_back_card_image_path() function."""

    def test_empty_directory_returns_none(self):
        """Directory with no images should return None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = get_back_card_image_path(tmpdir)
            assert result is None

    def test_non_image_files_returns_none(self):
        """Directory with only non-image files should return None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            txt_path = os.path.join(tmpdir, 'readme.txt')
            with open(txt_path, 'w') as f:
                f.write('not an image')

            result = get_back_card_image_path(tmpdir)
            assert result is None

    def test_single_image_returns_path(self):
        """Directory with one image should return that image's path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            img = Image.new('RGB', (100, 100), color='red')
            img_path = os.path.join(tmpdir, 'back.png')
            img.save(img_path, 'PNG')

            result = get_back_card_image_path(tmpdir)
            assert result is not None
            assert str(result).endswith('back.png')


class TestCropAndScaleImage:
    """Tests for crop_and_scale_image() function."""

    def test_stretch_real_bleed_both_axes(self):
        """STRETCH with enough source pixels should use real bleed on both axes."""
        # 300x420 source, 20% crop → cropped 240x336, ratio 1.2
        # unscaled bleed: 210*1.2=252 <= 300, 290*1.2=348 <= 420
        img = Image.new('RGB', (300, 420), color='red')
        result_img, off_x, off_y, synth = crop_and_scale_image(
            img, 20, 20, 200, 280, 5, 5, FitMode.STRETCH
        )
        assert result_img.size == (210, 290)
        assert off_x == -5
        assert off_y == -5
        assert synth == (0, 0)

    def test_stretch_no_room_for_bleed(self):
        """STRETCH without room for bleed should fall back to synthetic bleed."""
        # 200x280 source, 10% crop → cropped 180x252, ratio 0.9
        # unscaled bleed: 300*0.9=270 > 200
        img = Image.new('RGB', (200, 280), color='red')
        result_img, off_x, off_y, synth = crop_and_scale_image(
            img, 10, 10, 200, 280, 50, 50, FitMode.STRETCH
        )
        assert result_img.size == (200, 280)
        assert off_x == 0
        assert off_y == 0
        assert synth == (50, 50)

    def test_zero_crop_zero_bleed(self):
        """Zero crop and zero bleed should resize to target dimensions."""
        img = Image.new('RGB', (500, 700), color='red')
        result_img, off_x, off_y, synth = crop_and_scale_image(
            img, 0, 0, 200, 280, 0, 0, FitMode.STRETCH
        )
        assert result_img.size == (200, 280)
        assert off_x == 0
        assert off_y == 0
        assert synth == (0, 0)

    def test_crop_mode_real_bleed_both(self):
        """CROP mode with room on both axes should use real bleed."""
        # 300x420 source, 20% crop, uniform ratio = min(240/200, 336/280) = 1.2
        # unscaled bleed: 210*1.2=252 <= 300, 290*1.2=348 <= 420
        img = Image.new('RGB', (300, 420), color='red')
        result_img, off_x, off_y, synth = crop_and_scale_image(
            img, 20, 20, 200, 280, 5, 5, FitMode.CROP
        )
        assert result_img.size == (210, 290)
        assert off_x == -5
        assert off_y == -5
        assert synth == (0, 0)

    def test_crop_mode_real_bleed_x_only(self):
        """CROP mode with wide source should have real X bleed, synthetic Y."""
        # 300x280 source, 0% crop, uniform ratio = min(1.5, 1.0) = 1.0
        # unscaled X: 220*1.0=220 <= 300, unscaled Y: 300*1.0=300 > 280
        img = Image.new('RGB', (300, 280), color='red')
        result_img, off_x, off_y, synth = crop_and_scale_image(
            img, 0, 0, 200, 280, 10, 10, FitMode.CROP
        )
        assert result_img.size == (220, 280)
        assert off_x == -10
        assert off_y == 0
        assert synth == (0, 10)

    def test_crop_mode_real_bleed_y_only(self):
        """CROP mode with tall source should have synthetic X, real Y bleed."""
        # 200x420 source, 0% crop, uniform ratio = min(1.0, 1.5) = 1.0
        # unscaled X: 220*1.0=220 > 200, unscaled Y: 300*1.0=300 <= 420
        img = Image.new('RGB', (200, 420), color='red')
        result_img, off_x, off_y, synth = crop_and_scale_image(
            img, 0, 0, 200, 280, 10, 10, FitMode.CROP
        )
        assert result_img.size == (200, 300)
        assert off_x == 0
        assert off_y == -10
        assert synth == (10, 0)

    def test_crop_mode_neither_axis_bleeds(self):
        """CROP mode with tight source should use synthetic bleed on both axes."""
        # 200x280 source, 0% crop, uniform ratio = 1.0
        # unscaled X: 220 > 200, unscaled Y: 300 > 280
        img = Image.new('RGB', (200, 280), color='red')
        result_img, off_x, off_y, synth = crop_and_scale_image(
            img, 0, 0, 200, 280, 10, 10, FitMode.CROP
        )
        assert result_img.size == (200, 280)
        assert off_x == 0
        assert off_y == 0
        assert synth == (10, 10)


class TestDrawCardWithBleed:
    """Tests for draw_card_with_bleed() function."""

    RED = (255, 0, 0)
    WHITE = (255, 255, 255)

    def test_card_placed_at_position(self):
        """Card should be pasted at the specified position.

            10        15        24       29
        10  +-------- +-------- +--------+
            | corner  | top     | corner |
        15  +-------- CCCCCCCCCC --------+
            | left    | card    | right  |
        24  +-------- CCCCCCCCCC --------+
            | corner  | bottom  | corner |
        29  +-------- +-------- +--------+

        C = card area, surrounding = bleed, outside = empty
        """
        card = Image.new('RGB', (10, 10), color='red')
        base = Image.new('RGB', (40, 40), color='white')
        draw_card_with_bleed(card, base, 15, 15, (5, 5))
        # Card area
        assert base.getpixel((15, 15)) == self.RED
        assert base.getpixel((24, 24)) == self.RED
        # Empty space (outside card and bleed)
        assert base.getpixel((0, 0)) == self.WHITE
        assert base.getpixel((39, 39)) == self.WHITE

    def test_edge_bleed_extends(self):
        """Edge bleed should extend the card's border pixels outward.

            10        15        24       29
        10  +-------- +-------- +--------+
            | corner  |*top*    | corner |
        15  +-------- CCCCCCCCCC --------+
            |*left*   | card    |*right* |
        24  +-------- CCCCCCCCCC --------+
            | corner  |*bottom* | corner |
        29  +-------- +-------- +--------+

        *edge* = edge bleed regions checked in this test
        Pixels at x/y = 9 and 30 (just outside) should be empty.
        """
        card = Image.new('RGB', (10, 10), color='red')
        base = Image.new('RGB', (40, 40), color='white')
        draw_card_with_bleed(card, base, 15, 15, (5, 5))
        # Top bleed: top row extended upward
        assert base.getpixel((15, 14)) == self.RED
        assert base.getpixel((15, 10)) == self.RED
        # Left bleed: left column extended leftward
        assert base.getpixel((14, 15)) == self.RED
        assert base.getpixel((10, 15)) == self.RED
        # Bottom bleed
        assert base.getpixel((15, 25)) == self.RED
        assert base.getpixel((15, 29)) == self.RED
        # Right bleed
        assert base.getpixel((25, 15)) == self.RED
        assert base.getpixel((29, 15)) == self.RED
        # Beyond bleed should remain empty
        assert base.getpixel((15, 9)) == self.WHITE
        assert base.getpixel((9, 15)) == self.WHITE
        assert base.getpixel((15, 30)) == self.WHITE
        assert base.getpixel((30, 15)) == self.WHITE

    def test_corner_bleed_fills(self):
        """Corner bleed regions should be filled with corner pixel color.

            10        15        24       29
        10  *TL*      +-------- +      *TR*
            |         | top     |        |
        15  +-------- CCCCCCCCCC --------+
            | left    | card    | right  |
        24  +-------- CCCCCCCCCC --------+
            |         | bottom  |        |
        29  *BL*      +-------- +      *BR*

        *XX* = corner bleed regions checked in this test
        Pixels at x/y = 9 and 30 (just outside) should be empty.
        """
        card = Image.new('RGB', (10, 10), color='red')
        base = Image.new('RGB', (40, 40), color='white')
        draw_card_with_bleed(card, base, 15, 15, (5, 5))
        # Top-left corner bleed region
        assert base.getpixel((10, 10)) == self.RED
        assert base.getpixel((14, 14)) == self.RED
        # Top-right corner bleed region
        assert base.getpixel((25, 10)) == self.RED
        assert base.getpixel((29, 14)) == self.RED
        # Bottom-left corner bleed region
        assert base.getpixel((10, 25)) == self.RED
        assert base.getpixel((14, 29)) == self.RED
        # Bottom-right corner bleed region
        assert base.getpixel((25, 25)) == self.RED
        assert base.getpixel((29, 29)) == self.RED
        # Outside corner bleed should remain empty
        assert base.getpixel((9, 9)) == self.WHITE
        assert base.getpixel((30, 9)) == self.WHITE
        assert base.getpixel((9, 30)) == self.WHITE
        assert base.getpixel((30, 30)) == self.WHITE

    def test_zero_bleed(self):
        """Zero bleed should just place the card with no bleed extension.

        15       24
        CCCCCCCCCC
        C  card  C
        CCCCCCCCCC

        No bleed regions — pixels at x=14, x=25, y=14, y=25
        should all be empty.
        """
        card = Image.new('RGB', (10, 10), color='red')
        base = Image.new('RGB', (40, 40), color='white')
        draw_card_with_bleed(card, base, 15, 15, (0, 0))
        # Card area
        assert base.getpixel((15, 15)) == self.RED
        assert base.getpixel((24, 24)) == self.RED
        # Adjacent pixels outside card should remain empty (no bleed)
        assert base.getpixel((14, 15)) == self.WHITE
        assert base.getpixel((15, 14)) == self.WHITE
        assert base.getpixel((25, 15)) == self.WHITE
        assert base.getpixel((15, 25)) == self.WHITE


class TestDrawCardLayout:
    """Tests for draw_card_layout() function."""

    RED = (255, 0, 0)
    BLUE = (0, 0, 255)
    GREEN = (0, 128, 0)
    YELLOW = (255, 255, 0)
    WHITE = (255, 255, 255)

    def test_single_card_placed(self):
        """Single card in 1x1 layout should be placed at the layout position.

        Base 300x400, card 100x140 at (50,50):

           0    50       149         299
        0  +----+--------+-----------+
           |    |        |           |
        50 | .. RRRRRRRRRR ......... |
           |    R  card  R   empty   |
       189 | .. RRRRRRRRRR ......... |
           |    |        |           |
       399 +----+--------+-----------+

        R = red card, . = empty (white)
        """
        card = Image.new('RGB', (100, 140), color='red')
        back = Image.new('RGB', (100, 140), color='blue')
        base = Image.new('RGB', (300, 400), color='white')

        draw_card_layout(
            card_images=[card],
            single_back_image=back,
            base_image=base,
            num_rows=1, num_cols=1,
            x_pos=[50], y_pos=[50],
            width=100, height=140,
            print_bleed=(0, 0),
            crop=(0, 0), crop_backs=(0, 0),
            ppi_ratio=1.0, extend_edges=0, extend_edges_backs=0, extend_corners_radius=0, extend_corners_backs_radius=0, extend_bleed=0,
            flip=False, fit=FitMode.STRETCH, fit_backs=FitMode.STRETCH,
            orientation=Orientation.PORTRAIT
        )
        assert base.getpixel((50, 50)) == self.RED
        assert base.getpixel((100, 100)) == self.RED
        # Outside card area should remain white
        assert base.getpixel((0, 0)) == (255, 255, 255)

    def test_none_card_skipped(self):
        """None entries in card list should leave base image unchanged.

        Base 300x400, card_images=[None]:

        0                          299
        +==========================+
        |                          |
        |    entirely empty        |
        |    (no card drawn)       |
        |                          |
        +==========================+
        """
        back = Image.new('RGB', (100, 140), color='blue')
        base = Image.new('RGB', (300, 400), color='white')
        original_data = list(base.tobytes())

        draw_card_layout(
            card_images=[None],
            single_back_image=back,
            base_image=base,
            num_rows=1, num_cols=1,
            x_pos=[50], y_pos=[50],
            width=100, height=140,
            print_bleed=(0, 0),
            crop=(0, 0), crop_backs=(0, 0),
            ppi_ratio=1.0, extend_edges=0, extend_edges_backs=0, extend_corners_radius=0, extend_corners_backs_radius=0, extend_bleed=0,
            flip=False, fit=FitMode.STRETCH, fit_backs=FitMode.STRETCH,
            orientation=Orientation.PORTRAIT
        )
        assert list(base.tobytes()) == original_data

    def test_flip_reverses_row_order(self):
        """Flip should place first card at bottom row and second at top.

        Base 300x500, 2 rows x 1 col, flip=True:

        Normal order:        Flipped order:

          50  +--------+       50  +--------+
              | red    |           | blue   |
         189  +--------+      189  +--------+
              |        |           |        |
         250  +--------+      250  +--------+
              | blue   |           | red    |
         389  +--------+      389  +--------+
        """
        red_card = Image.new('RGB', (100, 140), color='red')
        blue_card = Image.new('RGB', (100, 140), color='blue')
        back = Image.new('RGB', (100, 140), color='green')
        base = Image.new('RGB', (300, 500), color='white')

        draw_card_layout(
            card_images=[red_card, blue_card],
            single_back_image=back,
            base_image=base,
            num_rows=2, num_cols=1,
            x_pos=[50], y_pos=[50, 250],
            width=100, height=140,
            print_bleed=(0, 0),
            crop=(0, 0), crop_backs=(0, 0),
            ppi_ratio=1.0, extend_edges=0, extend_edges_backs=0, extend_corners_radius=0, extend_corners_backs_radius=0, extend_bleed=0,
            flip=True, fit=FitMode.STRETCH, fit_backs=FitMode.STRETCH,
            orientation=Orientation.LANDSCAPE
        )
        # With flip: card 0 (red) goes to row 1 (y=250), card 1 (blue) to row 0 (y=50)
        # Images are rotated 180 degrees, but still the same color
        assert base.getpixel((50, 250)) == self.RED
        assert base.getpixel((50, 50)) == self.BLUE

    def test_multi_card_grid(self):
        """2x2 grid should place 4 cards at the correct positions.

        Base 300x400, 2x2 grid:

           10       109  150      249
        10 RRRRRRRRRR    BBBBBBBBBB
           R card0  R    B card1  B
       149 RRRRRRRRRR    BBBBBBBBBB

       200 GGGGGGGGGG    YYYYYYYYYY
           G card2  G    Y card3  Y
       339 GGGGGGGGGG    YYYYYYYYYY

        R=red, B=blue, G=green, Y=yellow
        """
        cards = [
            Image.new('RGB', (100, 140), color='red'),
            Image.new('RGB', (100, 140), color='blue'),
            Image.new('RGB', (100, 140), color='green'),
            Image.new('RGB', (100, 140), color='yellow'),
        ]
        back = Image.new('RGB', (100, 140), color='gray')
        base = Image.new('RGB', (300, 400), color='white')

        draw_card_layout(
            card_images=cards,
            single_back_image=back,
            base_image=base,
            num_rows=2, num_cols=2,
            x_pos=[10, 150], y_pos=[10, 200],
            width=100, height=140,
            print_bleed=(0, 0),
            crop=(0, 0), crop_backs=(0, 0),
            ppi_ratio=1.0, extend_edges=0, extend_edges_backs=0, extend_corners_radius=0, extend_corners_backs_radius=0, extend_bleed=0,
            flip=False, fit=FitMode.STRETCH, fit_backs=FitMode.STRETCH,
            orientation=Orientation.PORTRAIT
        )
        # Card 0 (red) at top-left
        assert base.getpixel((10, 10)) == self.RED
        assert base.getpixel((109, 149)) == self.RED
        # Card 1 (blue) at top-right
        assert base.getpixel((150, 10)) == self.BLUE
        assert base.getpixel((249, 149)) == self.BLUE
        # Card 2 (green) at bottom-left
        assert base.getpixel((10, 200)) == self.GREEN
        assert base.getpixel((109, 339)) == self.GREEN
        # Card 3 (yellow) at bottom-right
        assert base.getpixel((150, 200)) == self.YELLOW
        assert base.getpixel((249, 339)) == self.YELLOW
        # Empty space between cards
        assert base.getpixel((130, 10)) == self.WHITE
        assert base.getpixel((10, 170)) == self.WHITE

    def test_print_bleed_extends_around_card(self):
        """Print bleed should add colored border around the card.

        Card 10x10 at (15,15), bleed 5px:

            10        15        24       29
        10  +-------- +-------- +--------+
            | corner  | top     | corner |
        15  +-------- CCCCCCCCCC --------+
            | left    | card    | right  |
        24  +-------- CCCCCCCCCC --------+
            | corner  | bottom  | corner |
        29  +-------- +-------- +--------+

        C = card, surrounding = bleed, outside = empty
        """
        card = Image.new('RGB', (10, 10), color='red')
        back = Image.new('RGB', (10, 10), color='blue')
        base = Image.new('RGB', (40, 40), color='white')

        draw_card_layout(
            card_images=[card],
            single_back_image=back,
            base_image=base,
            num_rows=1, num_cols=1,
            x_pos=[15], y_pos=[15],
            width=10, height=10,
            print_bleed=(5, 5),
            crop=(0, 0), crop_backs=(0, 0),
            ppi_ratio=1.0, extend_edges=0, extend_edges_backs=0, extend_corners_radius=0, extend_corners_backs_radius=0, extend_bleed=0,
            flip=False, fit=FitMode.STRETCH, fit_backs=FitMode.STRETCH,
            orientation=Orientation.PORTRAIT
        )
        # Card area
        assert base.getpixel((15, 15)) == self.RED
        assert base.getpixel((24, 24)) == self.RED
        # Bleed area
        assert base.getpixel((15, 10)) == self.RED
        assert base.getpixel((10, 15)) == self.RED
        assert base.getpixel((15, 29)) == self.RED
        assert base.getpixel((29, 15)) == self.RED
        # Corner bleed
        assert base.getpixel((10, 10)) == self.RED
        assert base.getpixel((29, 29)) == self.RED
        # Empty space beyond bleed
        assert base.getpixel((9, 15)) == self.WHITE
        assert base.getpixel((15, 9)) == self.WHITE
        assert base.getpixel((30, 15)) == self.WHITE
        assert base.getpixel((15, 30)) == self.WHITE

    def test_ppi_ratio_scales_positions_and_size(self):
        """ppi_ratio=2.0 should double all positions and sizes.

        Card 10x10 at pos (10,10), ppi_ratio=2.0:
        Scaled position = (20,20), scaled size = 20x20.

           20       39
        20 CCCCCCCCCC
           C  card  C
        39 CCCCCCCCCC

        Everything is doubled from the unscaled values.
        """
        card = Image.new('RGB', (10, 10), color='red')
        back = Image.new('RGB', (10, 10), color='blue')
        base = Image.new('RGB', (80, 80), color='white')

        draw_card_layout(
            card_images=[card],
            single_back_image=back,
            base_image=base,
            num_rows=1, num_cols=1,
            x_pos=[10], y_pos=[10],
            width=10, height=10,
            print_bleed=(0, 0),
            crop=(0, 0), crop_backs=(0, 0),
            ppi_ratio=2.0, extend_edges=0, extend_edges_backs=0, extend_corners_radius=0, extend_corners_backs_radius=0, extend_bleed=0,
            flip=False, fit=FitMode.STRETCH, fit_backs=FitMode.STRETCH,
            orientation=Orientation.PORTRAIT
        )
        # Card at scaled position (20,20) with scaled size 20x20
        assert base.getpixel((20, 20)) == self.RED
        assert base.getpixel((39, 39)) == self.RED
        # Just outside the card should be empty
        assert base.getpixel((19, 20)) == self.WHITE
        assert base.getpixel((20, 19)) == self.WHITE
        assert base.getpixel((40, 20)) == self.WHITE
        assert base.getpixel((20, 40)) == self.WHITE

    def test_crop_trims_front_card_edges(self):
        """crop=(50, 50) should crop 50% off the card before scaling.

        Card 200x200 with blue 50px border, red 100x100 center:

        BBBBBBBBBBBBBBBBBBBB        After 50% crop,
        BB                BB        only center red
        BB   RRRRRRRRRR   BB   ->   region remains,
        BB   R center R   BB        stretched to fit.
        BB   RRRRRRRRRR   BB
        BB                BB
        BBBBBBBBBBBBBBBBBBBB

        Result: card area should be red (center survived crop).
        """
        card = Image.new('RGB', (200, 200), color='blue')
        # Paint red center (50,50)-(149,149)
        for x in range(50, 150):
            for y in range(50, 150):
                card.putpixel((x, y), (255, 0, 0))
        back = Image.new('RGB', (200, 200), color='gray')
        base = Image.new('RGB', (200, 200), color='white')

        draw_card_layout(
            card_images=[card],
            single_back_image=back,
            base_image=base,
            num_rows=1, num_cols=1,
            x_pos=[50], y_pos=[50],
            width=100, height=100,
            print_bleed=(0, 0),
            crop=(50, 50), crop_backs=(0, 0),
            ppi_ratio=1.0, extend_edges=0, extend_edges_backs=0, extend_corners_radius=0, extend_corners_backs_radius=0, extend_bleed=0,
            flip=False, fit=FitMode.STRETCH, fit_backs=FitMode.STRETCH,
            orientation=Orientation.PORTRAIT
        )
        # Card area should be red (cropped to center, then stretched)
        assert base.getpixel((50, 50)) == self.RED
        assert base.getpixel((100, 100)) == self.RED
        assert base.getpixel((149, 149)) == self.RED
        # Outside card should be empty
        assert base.getpixel((49, 50)) == self.WHITE
        assert base.getpixel((150, 50)) == self.WHITE

    def test_crop_backs_applies_to_back_image(self):
        """crop_backs should be used instead of crop when card is the back.

        Back 200x200 with green 50px border, red 100x100 center.
        crop=(0,0), crop_backs=(50,50).

        Since card `is` single_back_image, crop_backs is used.
        Result: card area should be red (center survived crop).
        """
        back = Image.new('RGB', (200, 200), color='green')
        for x in range(50, 150):
            for y in range(50, 150):
                back.putpixel((x, y), self.RED)
        base = Image.new('RGB', (200, 200), color='white')

        draw_card_layout(
            card_images=[back],
            single_back_image=back,
            base_image=base,
            num_rows=1, num_cols=1,
            x_pos=[50], y_pos=[50],
            width=100, height=100,
            print_bleed=(0, 0),
            crop=(0, 0), crop_backs=(50, 50),
            ppi_ratio=1.0, extend_edges=0, extend_edges_backs=0, extend_corners_radius=0, extend_corners_backs_radius=0, extend_bleed=0,
            flip=False, fit=FitMode.STRETCH, fit_backs=FitMode.STRETCH,
            orientation=Orientation.PORTRAIT
        )
        # Card area should be red (crop_backs applied to center)
        assert base.getpixel((50, 50)) == self.RED
        assert base.getpixel((100, 100)) == self.RED
        assert base.getpixel((149, 149)) == self.RED
        # Outside card should be empty
        assert base.getpixel((49, 50)) == self.WHITE

    def test_fit_stretch_keeps_wide_card_edges(self):
        """STRETCH squishes a wide card, keeping left/right edge colors.

        Card 200x100: blue 20px left, green 20px right, red center.
        Target 100x100. STRETCH compresses full width into target.

        Resized: 10px blue | 80px red | 10px green

          50  59 60           139 140 149
          BBBBBBBBRRRRRRRRRRRRRGGGGGGGG
          B blue B     red    G green G
          BBBBBBBBRRRRRRRRRRRRRGGGGGGGG
        """
        card = Image.new('RGB', (200, 100), color='red')
        for x in range(20):
            for y in range(100):
                card.putpixel((x, y), self.BLUE)
        for x in range(180, 200):
            for y in range(100):
                card.putpixel((x, y), self.GREEN)
        back = Image.new('RGB', (200, 100), color='gray')
        base = Image.new('RGB', (200, 200), color='white')

        draw_card_layout(
            card_images=[card],
            single_back_image=back,
            base_image=base,
            num_rows=1, num_cols=1,
            x_pos=[50], y_pos=[50],
            width=100, height=100,
            print_bleed=(0, 0),
            crop=(0, 0), crop_backs=(0, 0),
            ppi_ratio=1.0, extend_edges=0, extend_edges_backs=0, extend_corners_radius=0, extend_corners_backs_radius=0, extend_bleed=0,
            flip=False, fit=FitMode.STRETCH, fit_backs=FitMode.STRETCH,
            orientation=Orientation.PORTRAIT
        )
        # Left edge should be blue (stretched but preserved)
        assert base.getpixel((50, 80)) == self.BLUE
        # Right edge should be green
        assert base.getpixel((149, 80)) == self.GREEN
        # Center should be red
        assert base.getpixel((100, 80)) == self.RED

    def test_fit_crop_removes_wide_card_edges(self):
        """CROP on a wide card center-crops, removing left/right edges.

        Card 200x100: blue 20px left, green 20px right, red center.
        Target 100x100. CROP center-crops 50px from each side.

        Cropped region is x=50..149 of original, all red.

          50       149
          RRRRRRRRRR
          R   red  R
          RRRRRRRRRR
        """
        card = Image.new('RGB', (200, 100), color='red')
        for x in range(20):
            for y in range(100):
                card.putpixel((x, y), self.BLUE)
        for x in range(180, 200):
            for y in range(100):
                card.putpixel((x, y), (0, 128, 0))
        back = Image.new('RGB', (200, 100), color='gray')
        base = Image.new('RGB', (200, 200), color='white')

        draw_card_layout(
            card_images=[card],
            single_back_image=back,
            base_image=base,
            num_rows=1, num_cols=1,
            x_pos=[50], y_pos=[50],
            width=100, height=100,
            print_bleed=(0, 0),
            crop=(0, 0), crop_backs=(0, 0),
            ppi_ratio=1.0, extend_edges=0, extend_edges_backs=0, extend_corners_radius=0, extend_corners_backs_radius=0, extend_bleed=0,
            flip=False, fit=FitMode.CROP, fit_backs=FitMode.CROP,
            orientation=Orientation.PORTRAIT
        )
        # All edges should be red (blue/green sides were cropped off)
        assert base.getpixel((50, 80)) == self.RED
        assert base.getpixel((149, 80)) == self.RED
        assert base.getpixel((100, 80)) == self.RED
        # Outside card should be empty
        assert base.getpixel((49, 80)) == self.WHITE

    def test_fit_stretch_keeps_tall_card_edges(self):
        """STRETCH squishes a tall card, keeping top/bottom edge colors.

        Card 100x200: blue 20px top, green 20px bottom, red center.
        Target 100x100. STRETCH compresses full height into target.

        Resized: 10px blue / 80px red / 10px green

          50         149
        50 BBBBBBBBBBB
        59 BBBBBBBBBBB
        60 RRRRRRRRRRR
           R   red   R
       139 RRRRRRRRRRR
       140 GGGGGGGGGGG
       149 GGGGGGGGGGG
        """
        card = Image.new('RGB', (100, 200), color='red')
        for x in range(100):
            for y in range(20):
                card.putpixel((x, y), self.BLUE)
        for x in range(100):
            for y in range(180, 200):
                card.putpixel((x, y), self.GREEN)
        back = Image.new('RGB', (100, 200), color='gray')
        base = Image.new('RGB', (200, 200), color='white')

        draw_card_layout(
            card_images=[card],
            single_back_image=back,
            base_image=base,
            num_rows=1, num_cols=1,
            x_pos=[50], y_pos=[50],
            width=100, height=100,
            print_bleed=(0, 0),
            crop=(0, 0), crop_backs=(0, 0),
            ppi_ratio=1.0, extend_edges=0, extend_edges_backs=0, extend_corners_radius=0, extend_corners_backs_radius=0, extend_bleed=0,
            flip=False, fit=FitMode.STRETCH, fit_backs=FitMode.STRETCH,
            orientation=Orientation.PORTRAIT
        )
        # Top edge should be blue (stretched but preserved)
        assert base.getpixel((80, 50)) == self.BLUE
        # Bottom edge should be green
        assert base.getpixel((80, 149)) == self.GREEN
        # Center should be red
        assert base.getpixel((80, 100)) == self.RED

    def test_fit_crop_removes_tall_card_edges(self):
        """CROP on a tall card center-crops, removing top/bottom edges.

        Card 100x200: blue 20px top, green 20px bottom, red center.
        Target 100x100. CROP center-crops 50px from top and bottom.

        Cropped region is y=50..149 of original, all red.

          50         149
        50 RRRRRRRRRRR
           R   red   R
       149 RRRRRRRRRRR
        """
        card = Image.new('RGB', (100, 200), color='red')
        for x in range(100):
            for y in range(20):
                card.putpixel((x, y), self.BLUE)
        for x in range(100):
            for y in range(180, 200):
                card.putpixel((x, y), self.GREEN)
        back = Image.new('RGB', (100, 200), color='gray')
        base = Image.new('RGB', (200, 200), color='white')

        draw_card_layout(
            card_images=[card],
            single_back_image=back,
            base_image=base,
            num_rows=1, num_cols=1,
            x_pos=[50], y_pos=[50],
            width=100, height=100,
            print_bleed=(0, 0),
            crop=(0, 0), crop_backs=(0, 0),
            ppi_ratio=1.0, extend_edges=0, extend_edges_backs=0, extend_corners_radius=0, extend_corners_backs_radius=0, extend_bleed=0,
            flip=False, fit=FitMode.CROP, fit_backs=FitMode.CROP,
            orientation=Orientation.PORTRAIT
        )
        # All edges should be red (blue/green sides were cropped off)
        assert base.getpixel((80, 50)) == self.RED
        assert base.getpixel((80, 149)) == self.RED
        assert base.getpixel((80, 100)) == self.RED
        # Outside card should be empty
        assert base.getpixel((80, 49)) == self.WHITE

    def test_extend_edges_zero_keeps_border(self):
        """Without extend_edges, the card's blue border is visible.

        Card 30x30: blue 10px border, red 10x10 center.
        Target 30x30 at (15,15), extend_edges=0.

        15                44
        BBBBBBBBBBBBBBBBBBBB
        BB                BB
        BB  RRRRRRRRRRRR  BB
        BB  R  center  R  BB
        BB  RRRRRRRRRRRR  BB
        BB                BB
        BBBBBBBBBBBBBBBBBBBB

        Edges of placed card should be blue.
        """
        card = Image.new('RGB', (30, 30), color='blue')
        for x in range(10, 20):
            for y in range(10, 20):
                card.putpixel((x, y), (255, 0, 0))
        back = Image.new('RGB', (30, 30), color='gray')
        base = Image.new('RGB', (60, 60), color='white')

        draw_card_layout(
            card_images=[card],
            single_back_image=back,
            base_image=base,
            num_rows=1, num_cols=1,
            x_pos=[15], y_pos=[15],
            width=30, height=30,
            print_bleed=(0, 0),
            crop=(0, 0), crop_backs=(0, 0),
            ppi_ratio=1.0, extend_edges=0, extend_edges_backs=0, extend_corners_radius=0, extend_corners_backs_radius=0, extend_bleed=0,
            flip=False, fit=FitMode.STRETCH, fit_backs=FitMode.STRETCH,
            orientation=Orientation.PORTRAIT
        )
        # Edges of card should be blue (border preserved)
        assert base.getpixel((15, 15)) == self.BLUE
        assert base.getpixel((44, 15)) == self.BLUE
        assert base.getpixel((15, 44)) == self.BLUE
        assert base.getpixel((44, 44)) == self.BLUE
        # Center should be red
        assert base.getpixel((25, 25)) == self.RED

    def test_extend_edges_removes_border(self):
        """With extend_edges, the card's blue border is trimmed away.

        Card 30x30: blue 10px border, red 10x10 center.
        Target 30x30 at (15,15), extend_edges=10.
        Crops 10px from each edge -> 10x10 red card remains.
        Placed at (25,25) with 10px bleed of red around it.

            15        25      34       44
        15  +-------- +------ +--------+
            | bleed   | bleed | bleed  |
        25  +--------- RRRRRRR --------+
            | bleed   | card  | bleed  |
        34  +--------- RRRRRRR --------+
            | bleed   | bleed | bleed  |
        44  +-------- +------ +--------+

        Edges should now be red (blue border was trimmed).
        """
        card = Image.new('RGB', (30, 30), color='blue')
        for x in range(10, 20):
            for y in range(10, 20):
                card.putpixel((x, y), (255, 0, 0))
        back = Image.new('RGB', (30, 30), color='gray')
        base = Image.new('RGB', (60, 60), color='white')

        draw_card_layout(
            card_images=[card],
            single_back_image=back,
            base_image=base,
            num_rows=1, num_cols=1,
            x_pos=[15], y_pos=[15],
            width=30, height=30,
            print_bleed=(0, 0),
            crop=(0, 0), crop_backs=(0, 0),
            ppi_ratio=1.0, extend_edges=10, extend_edges_backs=0, extend_corners_radius=0, extend_corners_backs_radius=0, extend_bleed=0,
            flip=False, fit=FitMode.STRETCH, fit_backs=FitMode.STRETCH,
            orientation=Orientation.PORTRAIT
        )
        # Card area (25,25)-(34,34) should be red (border trimmed)
        assert base.getpixel((25, 25)) == self.RED
        assert base.getpixel((34, 34)) == self.RED
        # Bleed area should also be red (extended from red edges)
        assert base.getpixel((15, 25)) == self.RED
        assert base.getpixel((25, 15)) == self.RED
        assert base.getpixel((44, 25)) == self.RED
        assert base.getpixel((25, 44)) == self.RED
        # No blue should be visible anywhere in the card+bleed area
        assert base.getpixel((15, 15)) == self.RED
        assert base.getpixel((44, 44)) == self.RED
        # Outside bleed should be empty
        assert base.getpixel((14, 25)) == self.WHITE
        assert base.getpixel((25, 14)) == self.WHITE

    def test_extend_bleed_outer_edges_extended(self):
        """Outer edges of cards in a 2x2 grid should get extended bleed.

        Normal bleed: 5px, extended: 10px, total outer bleed: 15px
        - Top row: extended top edge (y=5 to y=19)
        - Bottom row: extended bottom edge (y=340 to y=354)
        - Left column: extended left edge (x=0 to x=9, clamped from x=-5)
        - Right column: extended right edge (x=250 to x=264)
        """
        red_card = Image.new('RGB', (100, 140), color='red')
        blue_card = Image.new('RGB', (100, 140), color='blue')
        green_card = Image.new('RGB', (100, 140), color='green')
        yellow_card = Image.new('RGB', (100, 140), color='yellow')
        back = Image.new('RGB', (100, 140), color='gray')
        base = Image.new('RGB', (300, 400), color='white')

        draw_card_layout(
            card_images=[red_card, blue_card, green_card, yellow_card],
            single_back_image=back,
            base_image=base,
            num_rows=2, num_cols=2,
            x_pos=[10, 150], y_pos=[20, 200],
            width=100, height=140,
            print_bleed=(5, 5),
            crop=(0, 0), crop_backs=(0, 0),
            ppi_ratio=1.0, extend_edges=0, extend_edges_backs=0, extend_corners_radius=0, extend_corners_backs_radius=0, extend_bleed=10,
            flip=False, fit=FitMode.STRETCH, fit_backs=FitMode.STRETCH,
            orientation=Orientation.PORTRAIT
        )

        # Top-left card (red): extended top and left
        assert base.getpixel((10, 5)) == self.RED      # Extended top bleed start
        assert base.getpixel((10, 19)) == self.RED     # Extended top bleed end
        assert base.getpixel((0, 20)) == self.RED      # Extended left bleed (clamped from x=-5)

        # Top-right card (blue): extended top and right
        assert base.getpixel((150, 5)) == self.BLUE    # Extended top bleed start
        assert base.getpixel((150, 19)) == self.BLUE   # Extended top bleed end
        assert base.getpixel((264, 20)) == self.BLUE   # Extended right bleed end (x=250+14)

        # Bottom-left card (green): extended bottom and left
        assert base.getpixel((10, 354)) == self.GREEN  # Extended bottom bleed end (y=340+14)
        assert base.getpixel((10, 355)) == self.WHITE  # Outside extended bleed
        assert base.getpixel((0, 200)) == self.GREEN   # Extended left bleed (clamped)

        # Bottom-right card (yellow): extended bottom and right
        assert base.getpixel((150, 354)) == self.YELLOW  # Extended bottom bleed end
        assert base.getpixel((150, 355)) == self.WHITE   # Outside extended bleed
        assert base.getpixel((264, 200)) == self.YELLOW  # Extended right bleed end

    def test_extend_bleed_zero_no_extra_bleed(self):
        """extend_bleed=0 should behave the same as not having the feature."""
        card = Image.new('RGB', (100, 140), color='red')
        back = Image.new('RGB', (100, 140), color='blue')
        base = Image.new('RGB', (300, 400), color='white')

        draw_card_layout(
            card_images=[card],
            single_back_image=back,
            base_image=base,
            num_rows=1, num_cols=1,
            x_pos=[50], y_pos=[50],
            width=100, height=140,
            print_bleed=(10, 10),
            crop=(0, 0), crop_backs=(0, 0),
            ppi_ratio=1.0, extend_edges=0, extend_edges_backs=0, extend_corners_radius=0, extend_corners_backs_radius=0, extend_bleed=0,
            flip=False, fit=FitMode.STRETCH, fit_backs=FitMode.STRETCH,
            orientation=Orientation.PORTRAIT
        )

        # Card at (50, 50), size 100x140, normal bleed 10px
        # Top bleed: 10 pixels from y=(50-10)=40 to y=49
        assert base.getpixel((50, 40)) == self.RED  # Normal top bleed
        assert base.getpixel((50, 39)) == self.WHITE  # Outside bleed

        # Bottom bleed: card ends at y=190, 10 pixels from y=190 to y=199
        assert base.getpixel((50, 199)) == self.RED  # Normal bottom bleed
        assert base.getpixel((50, 200)) == self.WHITE  # Outside bleed

    def test_extend_bleed_center_cards_no_extra(self):
        """Center cards in a 3x3 grid should not get extended bleed."""
        cards = [Image.new('RGB', (50, 70), color='red') for _ in range(9)]
        cards[4] = Image.new('RGB', (50, 70), color='blue')  # Center card
        back = Image.new('RGB', (50, 70), color='gray')
        base = Image.new('RGB', (300, 400), color='white')

        draw_card_layout(
            card_images=cards,
            single_back_image=back,
            base_image=base,
            num_rows=3, num_cols=3,
            x_pos=[10, 80, 150], y_pos=[10, 100, 190],
            width=50, height=70,
            print_bleed=(5, 5),
            crop=(0, 0), crop_backs=(0, 0),
            ppi_ratio=1.0, extend_edges=0, extend_edges_backs=0, extend_corners_radius=0, extend_corners_backs_radius=0, extend_bleed=10,
            flip=False, fit=FitMode.STRETCH, fit_backs=FitMode.STRETCH,
            orientation=Orientation.PORTRAIT
        )

        # Center card (blue) is at row=1, col=1, position (80, 100)
        # Should only have normal 5px bleed on all sides (no extended bleed)
        # Top bleed: 5 pixels from y=(100-5)=95 to y=99
        assert base.getpixel((80, 95)) == self.BLUE  # Normal top bleed
        assert base.getpixel((80, 94)) == self.WHITE  # No extended bleed

        # Bottom bleed: card ends at y=170, 5 pixels from y=170 to y=174
        assert base.getpixel((80, 174)) == self.BLUE  # Normal bottom bleed
        assert base.getpixel((80, 175)) == self.WHITE  # No extended bleed

    def test_extend_bleed_single_card_all_edges_extended(self):
        """A single card (1x1 grid) should get extended bleed on all four edges."""
        card = Image.new('RGB', (100, 140), color='red')
        back = Image.new('RGB', (100, 140), color='blue')
        base = Image.new('RGB', (300, 400), color='white')

        draw_card_layout(
            card_images=[card],
            single_back_image=back,
            base_image=base,
            num_rows=1, num_cols=1,
            x_pos=[50], y_pos=[50],
            width=100, height=140,
            print_bleed=(5, 5),
            crop=(0, 0), crop_backs=(0, 0),
            ppi_ratio=1.0, extend_edges=0, extend_edges_backs=0, extend_corners_radius=0, extend_corners_backs_radius=0, extend_bleed=10,
            flip=False, fit=FitMode.STRETCH, fit_backs=FitMode.STRETCH,
            orientation=Orientation.PORTRAIT
        )

        # Single card is both first and last row/col, so all edges extended
        # Card at (50, 50), size 100x140
        # Normal bleed: 5px, extended: 10px, total: 15px

        # Top: extends 15 pixels from y=(50-15)=35 to y=49 (range 0-14)
        assert base.getpixel((50, 35)) == self.RED
        assert base.getpixel((50, 34)) == self.WHITE

        # Bottom: card ends at y=190, extends 15 pixels from y=190 to y=204
        assert base.getpixel((50, 204)) == self.RED
        assert base.getpixel((50, 205)) == self.WHITE

        # Left: extends 15 pixels from x=(50-15)=35 to x=49
        assert base.getpixel((35, 50)) == self.RED
        assert base.getpixel((34, 50)) == self.WHITE

        # Right: card ends at x=150, extends 15 pixels from x=150 to x=164
        assert base.getpixel((164, 50)) == self.RED
        assert base.getpixel((165, 50)) == self.WHITE


class TestExtraLayoutPaths:
    """Tests for extra_layout_paths()."""

    def write_json(self, tmpdir, name, data=None):
        path = Path(tmpdir) / name
        with open(path, 'w') as f:
            json.dump(data or {}, f)
        return path

    def test_empty_when_nothing_configured(self):
        os.environ.pop(EXTRA_LAYOUTS_ENV, None)
        original_dir = utilities.EXTRA_LAYOUTS_DIR
        utilities.EXTRA_LAYOUTS_DIR = Path(tempfile.gettempdir()) / "scm-test-nonexistent-dir"
        try:
            assert extra_layout_paths() == []
        finally:
            utilities.EXTRA_LAYOUTS_DIR = original_dir

    def test_dir_files_sorted_before_env_files(self):
        with tempfile.TemporaryDirectory() as dir_tmpdir, tempfile.TemporaryDirectory() as env_tmpdir:
            b_path = self.write_json(dir_tmpdir, "b.json")
            a_path = self.write_json(dir_tmpdir, "a.json")
            env_path = self.write_json(env_tmpdir, "c.json")

            original_dir = utilities.EXTRA_LAYOUTS_DIR
            utilities.EXTRA_LAYOUTS_DIR = Path(dir_tmpdir)
            os.environ[EXTRA_LAYOUTS_ENV] = str(env_path)
            try:
                assert extra_layout_paths() == [a_path, b_path, env_path]
            finally:
                utilities.EXTRA_LAYOUTS_DIR = original_dir
                del os.environ[EXTRA_LAYOUTS_ENV]


class TestFindExtraLayoutOwner:
    """Tests for find_extra_layout_owner()."""

    def write_json(self, tmpdir, name, data):
        path = Path(tmpdir) / name
        with open(path, 'w') as f:
            json.dump(data, f)
        return path

    def test_finds_defining_file_among_several(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mtg_path = self.write_json(tmpdir, "a-mtg.json", {
                "card_sizes": {"mtg": {"width": "2.5in", "height": "3.5in"}},
            })
            sorcery_path = self.write_json(tmpdir, "b-sorcery.json", {
                "card_sizes": {"sorcery": {"width": "2.61in", "height": "3.74in"}},
            })
            original_dir = utilities.EXTRA_LAYOUTS_DIR
            utilities.EXTRA_LAYOUTS_DIR = Path(tmpdir)
            try:
                assert find_extra_layout_owner("card_sizes", "sorcery") == sorcery_path
                assert find_extra_layout_owner("card_sizes", "mtg") == mtg_path
            finally:
                utilities.EXTRA_LAYOUTS_DIR = original_dir

    def test_returns_none_when_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.write_json(tmpdir, "a.json", {
                "card_sizes": {"mtg": {"width": "2.5in", "height": "3.5in"}},
            })
            original_dir = utilities.EXTRA_LAYOUTS_DIR
            utilities.EXTRA_LAYOUTS_DIR = Path(tmpdir)
            try:
                assert find_extra_layout_owner("card_sizes", "nonexistent") is None
            finally:
                utilities.EXTRA_LAYOUTS_DIR = original_dir


class TestMergeExtraLayouts:
    """Tests for merge_extra_layouts()."""

    def base_config(self):
        return {
            "card_sizes": {"poker": {"width": "2.5in", "height": "3.5in"}},
            "paper_sizes": {"letter": {"width": "11in", "height": "8.5in"}},
            "layouts": {"letter": {"poker": {"default": {"orientation": "landscape", "version": 1}}}},
        }

    def write_extra_file(self, tmpdir, name, data):
        path = Path(tmpdir) / name
        with open(path, 'w') as f:
            json.dump(data, f)
        return str(path)

    def test_no_env_var_is_noop(self):
        os.environ.pop(EXTRA_LAYOUTS_ENV, None)
        config = self.base_config()
        result = merge_extra_layouts(config)
        assert result == self.base_config()

    def test_merges_new_card_size(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            extra_path = self.write_extra_file(tmpdir, "extra.json", {
                "card_sizes": {"mtg": {"width": "2.5in", "height": "3.5in"}},
            })
            os.environ[EXTRA_LAYOUTS_ENV] = extra_path
            try:
                config = merge_extra_layouts(self.base_config())
                assert config["card_sizes"]["mtg"] == {"width": "2.5in", "height": "3.5in"}
                assert config["card_sizes"]["poker"] == {"width": "2.5in", "height": "3.5in"}
            finally:
                del os.environ[EXTRA_LAYOUTS_ENV]

    def test_merges_new_layout_entry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            extra_path = self.write_extra_file(tmpdir, "extra.json", {
                "layouts": {"letter": {"mtg": {"default": {"orientation": "portrait", "version": 1}}}},
            })
            os.environ[EXTRA_LAYOUTS_ENV] = extra_path
            try:
                config = merge_extra_layouts(self.base_config())
                assert config["layouts"]["letter"]["mtg"]["default"]["orientation"] == "portrait"
                # Existing entry untouched
                assert config["layouts"]["letter"]["poker"]["default"]["orientation"] == "landscape"
            finally:
                del os.environ[EXTRA_LAYOUTS_ENV]

    def test_card_size_collision_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            extra_path = self.write_extra_file(tmpdir, "extra.json", {
                "card_sizes": {"poker": {"width": "1in", "height": "1in"}},
            })
            os.environ[EXTRA_LAYOUTS_ENV] = extra_path
            try:
                with pytest.raises(ValueError):
                    merge_extra_layouts(self.base_config())
            finally:
                del os.environ[EXTRA_LAYOUTS_ENV]

    def test_layout_collision_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            extra_path = self.write_extra_file(tmpdir, "extra.json", {
                "layouts": {"letter": {"poker": {"default": {"orientation": "portrait", "version": 1}}}},
            })
            os.environ[EXTRA_LAYOUTS_ENV] = extra_path
            try:
                with pytest.raises(ValueError):
                    merge_extra_layouts(self.base_config())
            finally:
                del os.environ[EXTRA_LAYOUTS_ENV]

    def test_multiple_files_merge_in_order(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path_a = self.write_extra_file(tmpdir, "a.json", {
                "card_sizes": {"mtg": {"width": "2.5in", "height": "3.5in"}},
            })
            path_b = self.write_extra_file(tmpdir, "b.json", {
                "card_sizes": {"sorcery": {"width": "2.61in", "height": "3.74in"}},
            })
            os.environ[EXTRA_LAYOUTS_ENV] = os.pathsep.join([path_a, path_b])
            try:
                config = merge_extra_layouts(self.base_config())
                assert "mtg" in config["card_sizes"]
                assert "sorcery" in config["card_sizes"]
            finally:
                del os.environ[EXTRA_LAYOUTS_ENV]

    def test_scans_extra_layouts_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.write_extra_file(tmpdir, "a.json", {
                "card_sizes": {"mtg": {"width": "2.5in", "height": "3.5in"}},
            })
            original_dir = utilities.EXTRA_LAYOUTS_DIR
            utilities.EXTRA_LAYOUTS_DIR = Path(tmpdir)
            try:
                config = merge_extra_layouts(self.base_config())
                assert config["card_sizes"]["mtg"] == {"width": "2.5in", "height": "3.5in"}
            finally:
                utilities.EXTRA_LAYOUTS_DIR = original_dir

    def test_missing_extra_layouts_dir_is_noop(self):
        os.environ.pop(EXTRA_LAYOUTS_ENV, None)
        original_dir = utilities.EXTRA_LAYOUTS_DIR
        utilities.EXTRA_LAYOUTS_DIR = Path(tempfile.gettempdir()) / "scm-test-nonexistent-dir"
        try:
            config = merge_extra_layouts(self.base_config())
            assert config == self.base_config()
        finally:
            utilities.EXTRA_LAYOUTS_DIR = original_dir

    def test_dir_file_collision_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.write_extra_file(tmpdir, "a.json", {
                "card_sizes": {"poker": {"width": "1in", "height": "1in"}},
            })
            original_dir = utilities.EXTRA_LAYOUTS_DIR
            utilities.EXTRA_LAYOUTS_DIR = Path(tmpdir)
            try:
                with pytest.raises(ValueError):
                    merge_extra_layouts(self.base_config())
            finally:
                utilities.EXTRA_LAYOUTS_DIR = original_dir

    def test_dir_files_merge_before_env_var_files(self):
        with tempfile.TemporaryDirectory() as dir_tmpdir, tempfile.TemporaryDirectory() as env_tmpdir:
            self.write_extra_file(dir_tmpdir, "a.json", {
                "card_sizes": {"mtg": {"width": "2.5in", "height": "3.5in"}},
            })
            env_path = self.write_extra_file(env_tmpdir, "b.json", {
                "card_sizes": {"sorcery": {"width": "2.61in", "height": "3.74in"}},
            })
            original_dir = utilities.EXTRA_LAYOUTS_DIR
            utilities.EXTRA_LAYOUTS_DIR = Path(dir_tmpdir)
            os.environ[EXTRA_LAYOUTS_ENV] = env_path
            try:
                config = merge_extra_layouts(self.base_config())
                assert "mtg" in config["card_sizes"]
                assert "sorcery" in config["card_sizes"]
            finally:
                utilities.EXTRA_LAYOUTS_DIR = original_dir
                del os.environ[EXTRA_LAYOUTS_ENV]


class TestAddFrontBackPages:
    """Tests for add_front_back_pages() function."""

    def test_appends_front_and_back(self):
        """With only_fronts=False, should append both front and back pages.

        pages[] -> [front, back]
        """
        front = Image.new('RGB', (300, 400), color='white')
        back = Image.new('RGB', (300, 400), color='white')
        pages = []

        add_front_back_pages(
            front, back, pages,
            page_width=300, page_height=400,
            ppi_ratio=1.0, template='test_v1',
            only_fronts=False, label=None,
            orientation=Orientation.LANDSCAPE, label_margin_px=10, borderless=False
        )
        assert len(pages) == 2
        assert pages[0].size == front.size
        assert pages[1].size == back.size

    def test_only_fronts_appends_one(self):
        """With only_fronts=True, should append only the front page.

        pages[] -> [front]
        """
        front = Image.new('RGB', (300, 400), color='white')
        back = Image.new('RGB', (300, 400), color='white')
        pages = []

        add_front_back_pages(
            front, back, pages,
            page_width=300, page_height=400,
            ppi_ratio=1.0, template='test_v1',
            only_fronts=True, label=None,
            orientation=Orientation.LANDSCAPE, label_margin_px=10, borderless=False
        )
        assert len(pages) == 1
        assert pages[0].size == front.size

    def test_sheet_numbering_increments(self):
        """Sheet number should increment based on existing pages list size.

        Call 1: pages[] -> [front1, back1]
        Call 2: pages[] -> [front1, back1, front2, back2]
        """
        front1 = Image.new('RGB', (300, 400), color='white')
        back1 = Image.new('RGB', (300, 400), color='white')
        front2 = Image.new('RGB', (300, 400), color='white')
        back2 = Image.new('RGB', (300, 400), color='white')
        pages = []

        add_front_back_pages(
            front1, back1, pages,
            page_width=300, page_height=400,
            ppi_ratio=1.0, template='test_v1',
            only_fronts=False, label=None,
            orientation=Orientation.PORTRAIT, label_margin_px=10, borderless=False
        )
        add_front_back_pages(
            front2, back2, pages,
            page_width=300, page_height=400,
            ppi_ratio=1.0, template='test_v1',
            only_fronts=False, label=None,
            orientation=Orientation.PORTRAIT, label_margin_px=10, borderless=False
        )
        assert len(pages) == 4

    def test_name_label(self):
        """Providing a name should not raise (label includes name).

        pages[] -> [front, back]  (with name='my_deck')
        """
        front = Image.new('RGB', (300, 400), color='white')
        back = Image.new('RGB', (300, 400), color='white')
        pages = []

        add_front_back_pages(
            front, back, pages,
            page_width=300, page_height=400,
            ppi_ratio=1.0, template='test_v1',
            only_fronts=False, label='my_deck',
            orientation=Orientation.PORTRAIT, label_margin_px=10, borderless=False
        )
        assert len(pages) == 2


class TestGenerateRegMark:
    """Tests for page_manager.generate_reg_mark()."""

    def test_transparent_background(self):
        """The canvas is RGBA with a fully transparent background and an opaque
        registration mark."""
        img = page_manager.generate_reg_mark(
            paper_width='2in',
            paper_height='2in',
            inset='0.4in',
            thickness='0.02in',
            length='0.2in',
            dpi=100,
            registration=Registration.THREE,
        )
        assert img.mode == 'RGBA'

        # Corner is far from the registration mark, should be fully transparent.
        assert img.getpixel((0, 0))[3] == 0

        # The registration square is drawn near the bottom-left inset; scan for an opaque pixel.
        found_opaque = any(
            img.getpixel((x, y))[3] == 255
            for x in range(img.width)
            for y in range(img.height)
        )
        assert found_opaque, "Expected at least one fully opaque registration-mark pixel"

