import re
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

import numpy as np
from PIL import Image

import page_manager
import siser_marks
import utilities
from enums import Registration


class TestSiserMarks(unittest.TestCase):
    def test_registration_enum_includes_siser(self):
        self.assertEqual(Registration.SISER.value, "siser")
        self.assertIs(Registration("siser"), Registration.SISER)

    def test_siser_vector_page_marks_letter_geometry(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(siser_marks, "SISER_MARKS_DIR", Path(tmp) / "empty"):
                dpi = 300
                px_to_mm = 25.4 / dpi
                img = page_manager.generate_reg_mark(
                    paper_width="11in",
                    paper_height="8.5in",
                    inset="0.5in",
                    thickness="0.5mm",
                    length="10mm",
                    dpi=dpi,
                    registration=Registration.SISER,
                    paper_size_key="letter",
                    orientation_key="landscape",
                )
                self.assertEqual(img.size, (3300, 2550))
                arr = np.array(img)
                blk = (arr[:, :, 0] < 80) & (arr[:, :, 1] < 80) & (arr[:, :, 2] < 80)

                # Interior must stay clean white (no bottom-left square or stray marks)
                self.assertFalse(blk[300:2250, 300:3000].any())

                # Exact Leonardo Page Marks: 5.5 mm outer inset, 19.0 mm arm end
                ys, xs = np.where(blk)
                self.assertAlmostEqual(xs.min() * px_to_mm, 5.5, delta=0.15)
                self.assertAlmostEqual(xs.max() * px_to_mm, 279.4 - 5.5, delta=0.15)
                self.assertAlmostEqual(ys.min() * px_to_mm, 5.5, delta=0.15)
                self.assertAlmostEqual(ys.max() * px_to_mm, 215.9 - 5.5, delta=0.15)

    def test_siser_vector_page_marks_a4_geometry(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(siser_marks, "SISER_MARKS_DIR", Path(tmp) / "empty"):
                dpi = 300
                px_to_mm = 25.4 / dpi
                img = siser_marks.generate_siser_reg_mark(
                    paper_width_mm=297.0,
                    paper_height_mm=210.0,
                    dpi=dpi,
                    paper_size_key="a4",
                    orientation_key="landscape",
                )
                arr = np.array(img)
                blk = (arr[:, :, 0] < 80) & (arr[:, :, 1] < 80) & (arr[:, :, 2] < 80)
                ys, xs = np.where(blk)
                self.assertAlmostEqual(xs.min() * px_to_mm, 5.5, delta=0.15)
                self.assertAlmostEqual(xs.max() * px_to_mm, 297.0 - 5.5, delta=0.15)
                self.assertAlmostEqual(ys.min() * px_to_mm, 5.5, delta=0.15)
                self.assertAlmostEqual(ys.max() * px_to_mm, 210.0 - 5.5, delta=0.15)

    def test_build_leonardo_svg_single_closed_paths(self):
        layout = siser_marks._compute_scm_slots_mm("letter", "standard", borderless=False)
        svg_text = siser_marks.build_leonardo_svg_for_layout(layout, include_reference=False)

        root = ET.fromstring(svg_text)
        ns = {"svg": "http://www.w3.org/2000/svg"}
        paths = root.findall(".//svg:path", ns)
        self.assertEqual(len(paths), len(layout["slots"]))
        self.assertEqual(len(root.findall(".//svg:rect", ns)), 0)
        self.assertEqual(len(root.findall(".//svg:line", ns)), 0)
        self.assertEqual(len(root.findall(".//svg:text", ns)), 0)

        px_to_mm = 25.4 / 96.0
        expected_w = layout["slots"][0]["w_mm"]
        expected_h = layout["slots"][0]["h_mm"]
        for p in paths:
            d = p.attrib["d"]
            self.assertTrue(d.startswith("M ") and d.endswith("Z"))
            self.assertEqual(p.attrib["stroke"], "none")
            nums = [float(x) for x in re.findall(r"[-+]?\d*\.\d+|\d+", d)]
            xs, ys = nums[0::2], nums[1::2]
            self.assertAlmostEqual((max(xs) - min(xs)) * px_to_mm, expected_w, delta=0.01)
            self.assertAlmostEqual((max(ys) - min(ys)) * px_to_mm, expected_h, delta=0.01)

    def test_siser_generate_pdf_keeps_back_page_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            with mock.patch.object(siser_marks, "SISER_MARKS_DIR", tmp_path / "empty"):
                front_dir = tmp_path / "front"
                back_dir = tmp_path / "back"
                ds_dir = tmp_path / "ds"
                out_dir = tmp_path / "out"
                for d in (front_dir, back_dir, ds_dir, out_dir):
                    d.mkdir()

                Image.new("RGB", (750, 1050), (30, 120, 200)).save(front_dir / "card1.png")
                Image.new("RGB", (750, 1050), (180, 60, 40)).save(back_dir / "back.png")

                utilities.generate_pdf(
                    str(front_dir),
                    str(back_dir),
                    str(ds_dir),
                    str(out_dir),
                    True,       # output_images
                    "standard", # card_size
                    "letter",   # paper_size
                    "siser",    # registration
                    False,      # only_fronts
                    "stretch",  # fit
                    None,       # fit_backs
                    None,       # crop_string
                    None,       # crop_backs_string
                    None,       # extend_edges
                    None,       # extend_edges_backs
                    None,       # extend_corners
                    None,       # extend_corners_backs
                    None,       # extend_bleed
                    None,       # extend_bleed_backs
                    150,        # ppi
                    95,         # quality
                    (),         # skip_indices
                    False,      # load_offset
                    None,       # label
                    False,      # show_outline
                )

                out_files = sorted(out_dir.glob("*.png"))
                self.assertEqual(len(out_files), 2)
                page1 = np.array(Image.open(out_files[0]))
                page2 = np.array(Image.open(out_files[1]))

                # Front page has black top-left L-mark; back page corner must stay pure white
                self.assertTrue((page1[:120, :120].mean(axis=2) < 80).any())
                self.assertGreater(int(page2[:120, :120].min()), 240)


if __name__ == "__main__":
    unittest.main()
