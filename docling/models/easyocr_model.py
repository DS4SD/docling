import copy
import logging
from typing import Iterable, List, Tuple

import numpy
import numpy as np
from PIL import Image, ImageDraw
from rtree import index
from scipy.ndimage import find_objects, label

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

    def get_ocr_rects(self, page: Page) -> Tuple[bool, List[BoundingBox]]:
        BITMAP_COVERAGE_TRESHOLD = 0.75

        def find_ocr_rects(size, bitmap_rects):
            image = Image.new(
                "1", (round(size.width), round(size.height))
            )  # '1' mode is binary

            # Draw all bitmap rects into a binary image
            draw = ImageDraw.Draw(image)
            for rect in bitmap_rects:
                x0, y0, x1, y1 = rect.as_tuple()
                x0, y0, x1, y1 = round(x0), round(y0), round(x1), round(y1)
                draw.rectangle([(x0, y0), (x1, y1)], fill=1)

            np_image = np.array(image)

            # Find the connected components
            labeled_image, num_features = label(
                np_image > 0
            )  # Label black (0 value) regions

            # Find enclosing bounding boxes for each connected component.
            slices = find_objects(labeled_image)
            bounding_boxes = [
                BoundingBox(
                    l=slc[1].start,
                    t=slc[0].start,
                    r=slc[1].stop - 1,
                    b=slc[0].stop - 1,
                    coord_origin=CoordOrigin.TOPLEFT,
                )
                for slc in slices
            ]

            # Compute area fraction on page covered by bitmaps
            area_frac = np.sum(np_image > 0) / (size.width * size.height)

            return (area_frac, bounding_boxes)  # fraction covered  # boxes

        bitmap_rects = page._backend.get_bitmap_rects()
        coverage, ocr_rects = find_ocr_rects(page.size, bitmap_rects)

        # return full-page rectangle if sufficiently covered with bitmaps
        if coverage > BITMAP_COVERAGE_TRESHOLD:
            return [
                BoundingBox(
                    l=0,
                    t=0,
                    r=page.size.width,
                    b=page.size.height,
                    coord_origin=CoordOrigin.TOPLEFT,
                )
            ]
        # return individual rectangles if the bitmap coverage is smaller
        elif coverage < BITMAP_COVERAGE_TRESHOLD:
            return ocr_rects

    def __call__(self, page_batch: Iterable[Page]) -> Iterable[Page]:

        if not self.enabled:
            yield from page_batch
            return

        for page in page_batch:
            ocr_rects = self.get_ocr_rects(page)

            all_ocr_cells = []
            for ocr_rect in ocr_rects:
                high_res_image = page._backend.get_page_image(
                    scale=self.scale, cropbox=ocr_rect
                )
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
                                (line[0][0][0] / self.scale) + ocr_rect.l,
                                (line[0][0][1] / self.scale) + ocr_rect.t,
                                (line[0][2][0] / self.scale) + ocr_rect.l,
                                (line[0][2][1] / self.scale) + ocr_rect.t,
                            ),
                            origin=CoordOrigin.TOPLEFT,
                        ),
                    )
                    for ix, line in enumerate(result)
                ]
                all_ocr_cells.extend(cells)

            ## Remove OCR cells which overlap with programmatic cells.

            # Create R-tree index for programmatic cells
            p = index.Property()
            p.dimension = 2
            idx = index.Index(properties=p)

            for i, cell in enumerate(page.cells):
                idx.insert(i, cell.bbox.as_tuple())

            def is_overlapping_with_existing_cells(ocr_cell):
                # Query the R-tree to get overlapping rectangles
                possible_matches_index = list(
                    idx.intersection(ocr_cell.bbox.as_tuple())
                )

                return (
                    len(possible_matches_index) > 0
                )  # this is a weak criterion but it works.

            filtered_ocr_cells = [
                rect
                for rect in all_ocr_cells
                if not is_overlapping_with_existing_cells(rect)
            ]

            page.cells.extend(filtered_ocr_cells)

            # DEBUG code:
            def draw_clusters_and_cells():
                image = copy.deepcopy(page.image)
                draw = ImageDraw.Draw(image)

                for tc in page.cells:
                    x0, y0, x1, y1 = tc.bbox.as_tuple()
                    color = "red"
                    if isinstance(tc, OcrCell):
                        color = "magenta"
                    draw.rectangle([(x0, y0), (x1, y1)], outline=color)
                image.show()

            # draw_clusters_and_cells()

            yield page
