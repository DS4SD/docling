import logging
import tempfile
from typing import Iterable, Optional, Tuple

from docling_core.types.doc import BoundingBox, CoordOrigin

from docling.datamodel.base_models import OcrCell, Page
from docling.datamodel.document import ConversionResult
from docling.datamodel.pipeline_options import OcrMacOptions
from docling.datamodel.settings import settings
from docling.models.base_ocr_model import BaseOcrModel
from docling.utils.profiling import TimeRecorder

_log = logging.getLogger(__name__)


class OcrMacModel(BaseOcrModel):
    def __init__(self, enabled: bool, options: OcrMacOptions):
        super().__init__(enabled=enabled, options=options)
        self.options: OcrMacOptions

        self.scale = 3  # multiplier for 72 dpi == 216 dpi.

        if self.enabled:
            install_errmsg = (
                "ocrmac is not correctly installed. "
                "Please install it via `pip install ocrmac` to use this OCR engine. "
                "Alternatively, Docling has support for other OCR engines. See the documentation: "
                "https://ds4sd.github.io/docling/installation/"
            )
            try:
                from ocrmac import ocrmac
            except ImportError:
                raise ImportError(install_errmsg)

            self.reader_RIL = ocrmac.OCR

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

                    ocr_rects = self.get_ocr_rects(page)

                    all_ocr_cells = []
                    for ocr_rect in ocr_rects:
                        # Skip zero area boxes
                        if ocr_rect.area() == 0:
                            continue
                        high_res_image = page._backend.get_page_image(
                            scale=self.scale, cropbox=ocr_rect
                        )

                        with tempfile.NamedTemporaryFile(
                            suffix=".png", mode="w"
                        ) as image_file:
                            fname = image_file.name
                            high_res_image.save(fname)

                            boxes = self.reader_RIL(
                                fname,
                                recognition_level=self.options.recognition,
                                framework=self.options.framework,
                                language_preference=self.options.lang,
                            ).recognize()

                        im_width, im_height = high_res_image.size
                        cells = []
                        for ix, (text, confidence, box) in enumerate(boxes):
                            x = float(box[0])
                            y = float(box[1])
                            w = float(box[2])
                            h = float(box[3])

                            x1 = x * im_width
                            y2 = (1 - y) * im_height

                            x2 = x1 + w * im_width
                            y1 = y2 - h * im_height

                            left = x1 / self.scale
                            top = y1 / self.scale
                            right = x2 / self.scale
                            bottom = y2 / self.scale

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
