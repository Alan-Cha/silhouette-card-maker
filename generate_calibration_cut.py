"""
Generate cut-based calibration sheets for cutting machine alignment.

Produces, for each configured paper size, a two-page PDF and a matching DXF.
The front page shows registration marks plus a grid of black-ringed 10mm
circles; the DXF cuts those same circles out of the front page. The back
page shows the same grid, but each circle is nudged by a unique per-cell
pixel offset (in the same pixel units offset_pdf.py's --x_offset/--y_offset
expect), with that offset printed in red inside the ring.

Print the PDF double-sided with long-side flip, convert the DXF with
dxf_to_studio3.py (or import it into Silhouette Studio directly) using the
matching paper size, and cut. Flip over each resulting disc: whichever
disc's red-offset ring is best centered on the physical cut edge tells you
the true front/back offset for your printer.
"""

import os
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

import dxf_manager
import page_manager
import size_convert
from enums import Orientation, Registration
from utilities import load_layout_config

# Specify directory locations
SCRIPT_DIR = Path(__file__).parent
asset_directory = SCRIPT_DIR / 'assets'

# Static distance from page margin used for the page title labels, matching
# generate_calibration.py.
MARGIN = 150

CIRCLE_DIAMETER = "10mm"
CIRCLE_RADIUS = "5mm"

layout_config = load_layout_config()
reg = layout_config.defaults.registration.default

# Corner-exclusion buffer used for layout purposes, mirroring
# generate_dxf.py's generate_single_dxf.
total_length_mm = size_convert.size_to_mm(reg.length) + page_manager.REG_PADDING_MM

for paper_size, paper_def in layout_config.paper_sizes.items():
    # Force landscape (paper sizes are already stored as landscape: width is
    # the longer dimension). The rest of this codebase always emits landscape
    # PDF pages -- generate_pdf() explicitly rotates portrait content back to
    # landscape before saving -- because offset_pdf.py's +x/+y semantics and
    # dxf_to_studio3.py's mat setup assume a landscape page. Circles are
    # square, so forcing landscape here costs nothing.
    computed = page_manager.generate_layout(
        orientation=Orientation.LANDSCAPE,
        card_width=CIRCLE_DIAMETER,
        card_height=CIRCLE_DIAMETER,
        paper_width=paper_def.width,
        paper_height=paper_def.height,
        inset=reg.inset,
        length=f"{total_length_mm}mm",
        ppi=layout_config.ppi,
    )

    x_pos = computed.x_pos
    y_pos = computed.y_pos
    circle_px = computed.card_width_px
    page_width_px = computed.paper_width_px
    page_height_px = computed.paper_height_px

    num_cols = len(x_pos)
    num_rows = len(y_pos)
    half_x = num_cols // 2
    half_y = num_rows // 2

    thickness_px = size_convert.size_to_pixel(reg.thickness, layout_config.ppi)

    # Registration marks must be drawn at the actual max length this layout's
    # margins allow (computed.max_length_mm), not the flat 5mm default used
    # only for the corner-exclusion calculation above -- exactly the value
    # generate_dxf.py reports as `max_length`. Whatever value gets printed
    # here is what must be passed to dxf_to_studio3.py's --reg_length when
    # cutting, or Silhouette Studio will look for marks of the wrong size.
    reg_length = f"{computed.max_length_mm}mm"

    im = Image.new('RGB', (page_width_px, page_height_px), 'white')
    with im:
        font = ImageFont.truetype(os.path.join(asset_directory, 'arial.ttf'), 40)
        offset_font = ImageFont.truetype(os.path.join(asset_directory, 'arial.ttf'), 25)

        front_image = im.copy()
        with page_manager.generate_reg_mark(
            paper_def.width,
            paper_def.height,
            reg.inset,
            reg.thickness,
            reg_length,
            layout_config.ppi,
            Registration.THREE,
        ) as reg_im:
            front_image.paste(reg_im.resize((page_width_px, page_height_px)), (0, 0))
        front_draw = ImageDraw.Draw(front_image)
        front_draw.text((page_width_px // 2, MARGIN), 'Front', fill=(0, 0, 0), anchor="mt", font=font)

        back_image = im.copy()
        back_draw = ImageDraw.Draw(back_image)
        back_draw.text((page_width_px // 2, MARGIN), 'Back', fill=(0, 0, 0), anchor="mt", font=font)

        for x_index, x in enumerate(x_pos):
            for y_index, y in enumerate(y_pos):
                front_draw.ellipse(
                    [x, y, x + circle_px, y + circle_px],
                    outline='black',
                    width=thickness_px,
                )

                offset_x = x_index - half_x
                offset_y = y_index - half_y

                back_x = x + offset_x
                back_y = y + offset_y
                back_draw.ellipse(
                    [back_x, back_y, back_x + circle_px, back_y + circle_px],
                    outline='black',
                    width=thickness_px,
                )

                # Label uses standard math convention (positive Y up), matching
                # generate_calibration.py's coordinate labels.
                back_draw.text(
                    (back_x + circle_px // 2, back_y + circle_px // 2),
                    f'{offset_x:+d},{-offset_y:+d}',
                    fill="red",
                    anchor="mm",
                    font=offset_font,
                )

        card_list = [front_image, back_image.rotate(180)]
        pdf_path = os.path.join("calibration", f"{paper_size}-calibration-cut.pdf")
        card_list[0].save(pdf_path, save_all=True, append_images=card_list[1:], resolution=300, speed=0, subsampling=0, quality=100)

        # Replace auto-generated timestamps with a fixed placeholder so the PDF
        # doesn't show as modified in git when regenerated with identical content.
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        pdf_bytes = re.sub(rb'D:\d{14}Z', b'D:20000101000000Z', pdf_bytes)
        with open(pdf_path, 'wb') as f:
            f.write(pdf_bytes)

        dxf_path = os.path.join("calibration", f"{paper_size}-calibration-cut.dxf")
        dxf_manager.generate_dxf(
            CIRCLE_DIAMETER,
            CIRCLE_DIAMETER,
            CIRCLE_RADIUS,
            x_pos,
            y_pos,
            layout_config.ppi,
            output_path=dxf_path,
            shape="circle",
        )

        num_circles = num_cols * num_rows
        print(f'{paper_size}: {num_cols}x{num_rows} ({num_circles} circles), max_length={computed.max_length_mm}mm -> {pdf_path}, {dxf_path}')
        print(f'  When cutting, pass to dxf_to_studio3.py: --reg_length {computed.max_length_mm} --reg_thickness {size_convert.size_to_mm(reg.thickness)} --reg_inset {size_convert.size_to_mm(reg.inset)} --unit mm')
