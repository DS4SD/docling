import logging
from typing import Iterable

import numpy
from docling_core.types.doc import BoundingBox, CoordOrigin

from docling.datamodel.base_models import OcrCell, Page
from docling.datamodel.document import ConversionResult
from docling.datamodel.pipeline_options import PaddleOcrOptions
from docling.datamodel.settings import settings
from docling.models.base_ocr_model import BaseOcrModel
from docling.utils.profiling import TimeRecorder

_log = logging.getLogger(__name__)


class PaddleOcrModel(BaseOcrModel):
    def __init__(self, enabled: bool, options: PaddleOcrOptions):
        super().__init__(enabled=enabled, options=options)
        self.options: PaddleOcrOptions

        self.scale = 3  # multiplier for 72 dpi == 216 dpi.

        if self.enabled:
            try:
                from paddleocr import PaddleOCR, draw_ocr
            except ImportError:
                raise ImportError(
                    "PaddleOCR is not installed. Please install it via `pip install paddlepaddle` and `pip install paddleocr` to use this OCR engine. "
                    "Alternatively, Docling has support for other OCR engines. See the documentation."
                )

            self.reader = PaddleOCR(
                lang=self.options.lang[0],
                use_gpu=self.options.use_gpu,
                use_angle_cls=self.options.use_angle_cls, 
                show_log=self.options.show_log,
            )

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
                        im = numpy.array(high_res_image)
                        result = self.reader.ocr(im, cls=self.options.cls)[0]

                        del high_res_image
                        del im

                        cells = [
                            OcrCell(
                                id=ix,
                                text=line[1][0],
                                confidence=line[1][1],
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

                    # Post-process the cells
                    page.cells = self.post_process_cells(all_ocr_cells, page.cells)

                # DEBUG code:
                if settings.debug.visualize_ocr:
                    self.draw_ocr_rects_and_cells(conv_res, page, ocr_rects)

                yield page
