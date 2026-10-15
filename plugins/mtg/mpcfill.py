"""
MPCFill image fetching.

The MPCFill API is a Google Apps Script that returns base64-encoded card images.
Each HTTP request has significant latency due to the Google Apps Script cold-start
overhead, so fetching images one at a time is very slow for large decks.

MPCFillFetcher works in two phases to deal with this. First, parse_mpcfill_xml
walks the decklist and calls collect_slot() for every slot, which only records
which files each card ID is needed for. Then download() fetches each unique card
ID exactly once using a ThreadPoolExecutor (up to MAX_WORKERS concurrent
requests), and each worker writes all of that card's files itself.

Writing inside the worker means a decoded image is released as soon as its files
are on disk, so peak memory stays proportional to MAX_WORKERS rather than to the
size of the whole deck. That matters because the images are large: a 91-card deck
of high-resolution PNGs can total several hundred megabytes.
"""

import os
import time
from base64 import b64decode
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from glob import glob, escape as glob_escape

import requests

from .common import remove_nonalphanumeric
from utilities import guess_extension

session = requests.Session()

# Maximum number of concurrent HTTP requests while downloading.
# Each worker thread fetches one image at a time, so 8 workers means
# up to 8 simultaneous downloads.
MAX_WORKERS = 8

# Filename (without extension) used for the deck-wide <cardback> image.
# The name marks the file as plugin-managed so a later run can replace it
# without disturbing the other card backs the user keeps in game/back.
CARDBACK_STEM = 'mpcfill_cardback'

# The Apps Script intermittently 404s or returns an empty body under load, so
# give each card a few attempts before reporting it as missing.
MAX_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 2


def request_mpcfill(card_id: str) -> bytes:
    """Fetch a single card image from MPCFill API and return decoded bytes."""
    base_url = "https://script.google.com/macros/s/AKfycbw8laScKBfxda2Wb0g63gkYDBdy8NWNxINoC4xDOwnCQ3JMFdruam1MdmNmN4wI5k4/exec?id="
    r = session.get(base_url + card_id, headers={"user-agent": "silhouette-card-maker/0.1", "accept": "*/*"})
    r.raise_for_status()
    return b64decode(r.content)


def write_image(output_dir: str, stem: str, card_art: bytes) -> str:
    """
    Write an image as `stem` plus the extension sniffed from its bytes.

    A card's art can change format between runs (e.g. .jpg to .png). Leaving both
    files behind would make create_pdf.py's resolve_image_with_any_extension()
    fail with an ambiguous match, so any same-stem file is removed first.
    """
    extension = guess_extension(card_art)
    image_path = os.path.join(output_dir, stem + extension)

    for stale_path in glob(glob_escape(os.path.join(output_dir, stem)) + '.*'):
        if stale_path != image_path:
            os.remove(stale_path)

    with open(image_path, 'wb') as f:
        f.write(card_art)

    return image_path


@dataclass(frozen=True)
class ImageTarget:
    """One file to write once a card ID's image has been downloaded."""
    output_dir: str
    stem: str
    label: str


class MPCFillFetcher:
    """
    Collects the files an MPCFill order needs, then downloads them in parallel.

    Call collect_slot() for every slot (it is the handle_card callback that
    parse_mpcfill_xml expects) and collect_cardback() for the order's shared
    back, then call download() once to do all of the network work.
    """

    def __init__(self, front_img_dir: str, double_sided_dir: str, back_dir: str):
        self.front_img_dir = front_img_dir
        self.double_sided_dir = double_sided_dir
        self.back_dir = back_dir

        # card_id -> files that need this image. Duplicate card IDs (e.g. 6 copies
        # of the same basic land across different slots) collapse to one download.
        self._targets: dict[str, list[ImageTarget]] = {}

    def _add_target(self, card_id: str, output_dir: str, stem: str, label: str) -> None:
        self._targets.setdefault(card_id, []).append(ImageTarget(output_dir, stem, label))

    def collect_slot(self, slot: int, front_id: str, front_name: str, back_id: str | None, back_name: str | None) -> None:
        """
        Record the images one slot needs. Fetches nothing.

        Back images use the FRONT name so create_pdf.py can match them.
        """
        stem = f'{slot}{remove_nonalphanumeric(front_name)}'

        self._add_target(front_id, self.front_img_dir, stem, f'slot {slot} ({front_name})')

        if back_id:
            self._add_target(back_id, self.double_sided_dir, stem, f'slot {slot} back ({front_name})')

    def collect_cardback(self, card_id: str) -> None:
        """
        Record the order's <cardback>, the shared back for every plain slot.

        It goes in the back directory rather than double_sided because
        create_pdf.py applies a single back image to every card.
        """
        self._add_target(card_id, self.back_dir, CARDBACK_STEM, 'deck cardback')

    def _fetch_and_write(self, card_id: str) -> tuple[str, str | None]:
        """
        Fetch one card, retrying a few times, and write every file that needs it.

        Runs on a worker thread and returns an error message instead of raising,
        so one bad card ID does not abort the rest of the deck.
        """
        card_art = b''
        error = None

        for attempt in range(MAX_ATTEMPTS):
            if attempt:
                time.sleep(RETRY_DELAY_SECONDS)

            try:
                card_art = request_mpcfill(card_id)
            except Exception as e:
                error = str(e)
                continue

            if card_art:
                error = None
                break

            error = 'empty image response'

        if not card_art:
            return (card_id, error)

        for target in self._targets[card_id]:
            write_image(target.output_dir, target.stem, card_art)

        return (card_id, None)

    def download(self) -> None:
        """Download every collected image, writing files as they arrive."""
        card_ids = list(self._targets)

        if not card_ids:
            return

        total = len(card_ids)
        print(f'Fetching {total} images with {MAX_WORKERS} workers...')

        failed = 0
        completed = 0

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Submit all fetch tasks to the thread pool. Each call returns a Future
            # representing the pending result. as_completed() then yields each Future
            # as it finishes, not necessarily in submission order.
            futures = [executor.submit(self._fetch_and_write, card_id) for card_id in card_ids]

            for future in as_completed(futures):
                card_id, error = future.result()
                completed += 1

                if error is not None:
                    failed += 1
                    for target in self._targets[card_id]:
                        print(f'  Warning: no image for {target.label}: {error}')

                if completed % 10 == 0 or completed == total:
                    print(f'  Fetched {completed - failed}/{total} images')

        if failed:
            print(f'Fetch finished with {failed} of {total} images missing.')
        else:
            print('Fetch complete.')
