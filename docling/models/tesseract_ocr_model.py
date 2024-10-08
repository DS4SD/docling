import logging
from typing import Iterable

import numpy

from docling.datamodel.base_models import BoundingBox, CoordOrigin, OcrCell, Page
from docling.datamodel.pipeline_options import TesseractCliOcrOptions
from docling.models.base_ocr_model import BaseOcrModel

_log = logging.getLogger(__name__)


class TesseractOcrModel(BaseOcrModel):
    def __init__(self, enabled: bool, options: TesseractCliOcrOptions):
        super().__init__(enabled=enabled, options=options)
        self.options: TesseractCliOcrOptions

        self.scale = 3  # multiplier for 72 dpi == 216 dpi.
        self.reader = None

        if self.enabled:
            setup_errmsg = (
                "tesserocr is not correctly installed. "
                "Please install it via `pip install tesserocr` to use this OCR engine. "
                "Note that tesserocr might have to be manually compiled for working with"
                "your Tesseract installation. The Docling documentation provides examples for it. "
                "Alternatively, Docling has support for other OCR engines. See the documentation."
            )
            try:
                import tesserocr
            except ImportError:
                raise ImportError(setup_errmsg)

            try:
                tesseract_version = tesserocr.tesseract_version()
                _log.debug("Initializing TesserOCR: %s", tesseract_version)
            except:
                raise ImportError(setup_errmsg)

            # Initialize the tesseractAPI
            lang = "+".join(self.options.lang)
            if self.options.path is not None:
                self.reader = tesserocr.PyTessBaseAPI(
                    path=self.options.path,
                    lang=lang,
                    psm=tesserocr.PSM.AUTO,
                    init=True,
                    oem=tesserocr.OEM.DEFAULT,
                )
            else:
                self.reader = tesserocr.PyTessBaseAPI(
                    lang=lang,
                    psm=tesserocr.PSM.AUTO,
                    init=True,
                    oem=tesserocr.OEM.DEFAULT,
                )
            self.reader_RIL = tesserocr.RIL

    def __del__(self):
        if self.reader is not None:
            # Finalize the tesseractAPI
            self.reader.End()

    def __call__(self, page_batch: Iterable[Page]) -> Iterable[Page]:

        if not self.enabled:
            yield from page_batch
            return

        for page in page_batch:
            ocr_rects = self.get_ocr_rects(page)

            all_ocr_cells = []
            for ocr_rect in ocr_rects:
                # Skip zero area boxes
                if ocr_rect.area() == 0:
                    continue
                high_res_image = page._backend.get_page_image(
                    scale=self.scale, cropbox=ocr_rect
                )

                # Retrieve text snippets with their bounding boxes
                self.reader.SetImage(high_res_image)
                boxes = self.reader.GetComponentImages(self.reader_RIL.TEXTLINE, True)

                cells = []
                for ix, (im, box, _, _) in enumerate(boxes):
                    # Set the area of interest. Tesseract uses Bottom-Left for the origin
                    self.reader.SetRectangle(box["x"], box["y"], box["w"], box["h"])

                    # Extract text within the bounding box
                    text = self.reader.GetUTF8Text().strip()
                    confidence = self.reader.MeanTextConf()
                    left = box["x"] / self.scale
                    bottom = box["y"] / self.scale
                    right = (box["x"] + box["w"]) / self.scale
                    top = (box["y"] + box["h"]) / self.scale

                    cells.append(
                        OcrCell(
                            id=ix,
                            text=text,
                            confidence=confidence,
                            bbox=BoundingBox.from_tuple(
                                coord=(left, top, right, bottom),
                                origin=CoordOrigin.TOPLEFT,
                            ),
                        )
                    )

                # del high_res_image
                all_ocr_cells.extend(cells)

            ## Remove OCR cells which overlap with programmatic cells.
            filtered_ocr_cells = self.filter_ocr_cells(all_ocr_cells, page.cells)

            page.cells.extend(filtered_ocr_cells)

            # DEBUG code:
            # self.draw_ocr_rects_and_cells(page, ocr_rects)

            yield page
