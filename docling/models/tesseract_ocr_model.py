import logging
from typing import Iterable

from docling_core.types.doc import BoundingBox, CoordOrigin

from docling.datamodel.base_models import Cell, OcrCell, Page
from docling.datamodel.document import ConversionResult
from docling.datamodel.pipeline_options import TesseractOcrOptions
from docling.datamodel.settings import settings
from docling.models.base_ocr_model import BaseOcrModel
from docling.utils.profiling import TimeRecorder

_log = logging.getLogger(__name__)


class TesseractOcrModel(BaseOcrModel):
    def __init__(self, enabled: bool, options: TesseractOcrOptions):
        super().__init__(enabled=enabled, options=options)
        self.options: TesseractOcrOptions

        self.scale = 3  # multiplier for 72 dpi == 216 dpi.
        self.reader = None

        if self.enabled:
            install_errmsg = (
                "tesserocr is not correctly installed. "
                "Please install it via `pip install tesserocr` to use this OCR engine. "
                "Note that tesserocr might have to be manually compiled for working with "
                "your Tesseract installation. The Docling documentation provides examples for it. "
                "Alternatively, Docling has support for other OCR engines. See the documentation: "
                "https://ds4sd.github.io/docling/installation/"
            )
            missing_langs_errmsg = (
                "tesserocr is not correctly configured. No language models have been detected. "
                "Please ensure that the TESSDATA_PREFIX envvar points to tesseract languages dir. "
                "You can find more information how to setup other OCR engines in Docling "
                "documentation: "
                "https://ds4sd.github.io/docling/installation/"
            )

            try:
                import tesserocr
            except ImportError:
                raise ImportError(install_errmsg)
            try:
                tesseract_version = tesserocr.tesseract_version()
            except:
                raise ImportError(install_errmsg)

            _, tesserocr_languages = tesserocr.get_languages()
            if not tesserocr_languages:
                raise ImportError(missing_langs_errmsg)

            # Initialize the tesseractAPI
            _log.debug("Initializing TesserOCR: %s", tesseract_version)
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

    def __call__(
        self, conv_res: ConversionResult, page_batch: Iterable[Page]
    ) -> Iterable[Page]:

        if not self.enabled:
            yield from page_batch
            return

        for page in page_batch:
            assert page._backend is not None
            if not page._backend.is_valid():
                yield page
            else:
                with TimeRecorder(conv_res, "ocr"):

                    assert self.reader is not None

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
                        boxes = self.reader.GetComponentImages(
                            self.reader_RIL.TEXTLINE, True
                        )

                        cells = []
                        for ix, (im, box, _, _) in enumerate(boxes):
                            # Set the area of interest. Tesseract uses Bottom-Left for the origin
                            self.reader.SetRectangle(
                                box["x"], box["y"], box["w"], box["h"]
                            )

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

                    # Post-process the cells
                    page.cells = self.post_process_cells(all_ocr_cells, page.cells)

                # DEBUG code:
                if settings.debug.visualize_ocr:
                    self.draw_ocr_rects_and_cells(conv_res, page, ocr_rects)

                yield page
