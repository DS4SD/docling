import copy
import logging
import random
from typing import Iterable

import numpy
from PIL import ImageDraw

from docling.datamodel.base_models import BoundingBox, CoordOrigin, OcrCell, Page

_log = logging.getLogger(__name__)


class EasyOcrModel:
    def __init__(self, config):
        self.config = config
        self.enabled = config["enabled"]
        self.scale = 3  # multiplier for 72 dpi == 216 dpi.

        if self.enabled:
            import easyocr

            self.reader = easyocr.Reader(config["lang"])

    def __call__(self, page_batch: Iterable[Page]) -> Iterable[Page]:

        if not self.enabled:
            yield from page_batch
            return

        for page in page_batch:
            # rects = page._fpage.
            high_res_image = page._backend.get_page_image(scale=self.scale)
            im = numpy.array(high_res_image)
            result = self.reader.readtext(im)

            del high_res_image
            del im

            cells = [
                OcrCell(
                    id=ix,
                    text=line[1],
                    confidence=line[2],
                    bbox=BoundingBox.from_tuple(
                        coord=(
                            line[0][0][0] / self.scale,
                            line[0][0][1] / self.scale,
                            line[0][2][0] / self.scale,
                            line[0][2][1] / self.scale,
                        ),
                        origin=CoordOrigin.TOPLEFT,
                    ),
                )
                for ix, line in enumerate(result)
            ]

            page.cells = cells  # For now, just overwrites all digital cells.

            # DEBUG code:
            def draw_clusters_and_cells():
                image = copy.deepcopy(page.image)
                draw = ImageDraw.Draw(image)

                cell_color = (
                    random.randint(30, 140),
                    random.randint(30, 140),
                    random.randint(30, 140),
                )
                for tc in cells:
                    x0, y0, x1, y1 = tc.bbox.as_tuple()
                    draw.rectangle([(x0, y0), (x1, y1)], outline=cell_color)
                image.show()

            # draw_clusters_and_cells()

            yield page
