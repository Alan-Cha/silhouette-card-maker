import os
import subprocess

import click

@click.command()
@click.argument('deck_path')
@click.argument('plugin')
@click.argument('delete_images')

def cli(
    deck_path: str,
    plugin_path: str,
    delete_images: bool
):





