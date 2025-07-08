import os
#from typing import Tuple
#from xml.dom import ValidationErr

import click
#import json
#from pydantic import BaseModel
import pypdfium2 as pdfium

from utilities import load_saved_offset, offset_images, save_offset

output_directory = os.path.join('game', 'output')
default_output_pdf_path = os.path.join(output_directory, 'game.pdf')

@click.command()
@click.option("--pdf_path", default=default_output_pdf_path, help="The path of the input PDF.")
@click.option("--output_pdf_path", help="The desired path of the offset PDF.")
@click.option("-x", "--x_offset", type=int, help="The desired offset in the x-axis.")
@click.option("-y", "--y_offset", type=int, help="The desired offset in the y-axis.")
@click.option("-s", "--save", default=False, is_flag=True, help="Save the x and y offset values.")
@click.option("--ppi", default=300, type=click.IntRange(min=0), show_default=True, help="Pixels per inch (PPI) when creating PDF.")

def offset_pdf(pdf_path, output_pdf_path, x_offset, y_offset, save, ppi):
    new_x_offset = 0
    new_y_offset = 0

    saved_offset = load_saved_offset()
    if saved_offset is not None:
        new_x_offset = saved_offset.x_offset
        new_y_offset = saved_offset.y_offset

        print(f'Loaded x offset: {new_x_offset}, y offset: {new_y_offset}')

    # Check for new offset values
    if x_offset is not None:
        new_x_offset = x_offset
    
    if y_offset is not None:
        new_y_offset = y_offset

    print(f'Using x offset: {new_x_offset}, y offset: {new_y_offset}')

    # Save new offset
    if save:
        save_offset(new_x_offset, new_y_offset)
        print(f'Saved offset')

    pdf = pdfium.PdfDocument(pdf_path)

    # Get all the raw page images from the PDF
    raw_images = []
    for page_number in range(len(pdf)):
        print(f"Page {page_number + 1}")
        page = pdf.get_page(page_number)
        raw_images.append(page.render(ppi/72).to_pil())

    # Offset images
    final_images = offset_images(raw_images, new_x_offset, new_y_offset, ppi)

    # The default for output_pdf_path is the original path but with _offset.py appended to the end.
    if output_pdf_path is None:
        output_pdf_path = f'{pdf_path.removesuffix(".pdf")}_offset.pdf'

    final_images[0].save(output_pdf_path, save_all=True, append_images=final_images[1:], resolution=ppi, speed=0, subsampling=0, quality=100)
    print(f'Offset PDF: {output_pdf_path}')

if __name__ == '__main__':
    offset_pdf()