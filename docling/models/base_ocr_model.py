import copy
import logging
from abc import abstractmethod
from typing import Iterable, List, Tuple

import numpy as np
from PIL import Image, ImageDraw
from rtree import index
from scipy.ndimage import find_objects, label

from docling.datamodel.base_models import BoundingBox, CoordOrigin, OcrCell, Page
from docling.datamodel.pipeline_options import OcrOptions

_log = logging.getLogger(__name__)


class BaseOcrModel:
    def __init__(self, enabled: bool, options: OcrOptions):
        self.enabled = enabled
        self.options = options

    # Computes the optimum amount and coordinates of rectangles to OCR on a given page
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

    # Filters OCR cells by dropping any OCR cell that intersects with an existing programmatic cell.
    def filter_ocr_cells(self, ocr_cells, programmatic_cells):
        # Create R-tree index for programmatic cells
        p = index.Property()
        p.dimension = 2
        idx = index.Index(properties=p)
        for i, cell in enumerate(programmatic_cells):
            idx.insert(i, cell.bbox.as_tuple())

        def is_overlapping_with_existing_cells(ocr_cell):
            # Query the R-tree to get overlapping rectangles
            possible_matches_index = list(idx.intersection(ocr_cell.bbox.as_tuple()))

            return (
                len(possible_matches_index) > 0
            )  # this is a weak criterion but it works.

        filtered_ocr_cells = [
            rect for rect in ocr_cells if not is_overlapping_with_existing_cells(rect)
        ]
        return filtered_ocr_cells

    def draw_ocr_rects_and_cells(self, page, ocr_rects):
        image = copy.deepcopy(page.image)
        draw = ImageDraw.Draw(image, "RGBA")

        # Draw OCR rectangles as yellow filled rect
        for rect in ocr_rects:
            x0, y0, x1, y1 = rect.as_tuple()
            shade_color = (255, 255, 0, 40)  # transparent yellow
            draw.rectangle([(x0, y0), (x1, y1)], fill=shade_color, outline=None)

        # Draw OCR and programmatic cells
        for tc in page.cells:
            x0, y0, x1, y1 = tc.bbox.as_tuple()
            color = "red"
            if isinstance(tc, OcrCell):
                color = "magenta"
            draw.rectangle([(x0, y0), (x1, y1)], outline=color)
        image.show()

    @abstractmethod
    def __call__(self, page_batch: Iterable[Page]) -> Iterable[Page]:
        pass
