import os

import fitz  #PyMuPDF
import click

IMAGE_DIRECTORY = os.path.join('game','front')

@click.command()
@click.argument('pdf_path')
@click.argument('output_dir', default=IMAGE_DIRECTORY)

def cli(pdf_path:str, output_dir:str):
    ### Captures @click arguments
    extract_pdf(pdf_path, output_dir)

def extract_pdf(pdf_path:str, output_dir:str):
    pdf_file = fitz.open(pdf_path)

    for page_index in range(len(pdf_file)):
        page = pdf_file.load_page(page_index)
        image_list = page.get_images(full=True)

        if image_list:
            print(f'[+] Found a total of {len(image_list)} images on page {page_index}')
        else:
            print(f'[!] No images found on page', page_index)
        
        for image_index, img in enumerate(image_list, start = 1):
            xref = img[0]

            base_image = pdf_file.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]

            image_name = f'image{page_index+1}_{image_index}.{image_ext}'
            image_path = os.path.join(output_dir,image_name)

            with open(image_path, "wb") as f:
                f.write(image_bytes)
                print(f'[+] {image_path}')

if __name__ == '__main__':
    cli()
