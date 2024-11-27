import logging
from typing import Iterable

import numpy
from docling_core.types.doc import BoundingBox, CoordOrigin

from docling.datamodel.base_models import OcrCell, Page
from docling.datamodel.document import ConversionResult
from docling.datamodel.pipeline_options import RapidOcrOptions
from docling.datamodel.settings import settings
from docling.models.base_ocr_model import BaseOcrModel
from docling.utils.profiling import TimeRecorder

_log = logging.getLogger(__name__)


class RapidOcrModel(BaseOcrModel):
    def __init__(self, enabled: bool, options: RapidOcrOptions):
        super().__init__(enabled=enabled, options=options)
        self.options: RapidOcrOptions

        self.scale = 3  # multiplier for 72 dpi == 216 dpi.

        if self.enabled:
            try:
                from rapidocr_onnxruntime import RapidOCR  # type: ignore
            except ImportError:
                raise ImportError(
                    "RapidOCR is not installed. Please install it via `pip install rapidocr_onnxruntime` to use this OCR engine. "
                    "Alternatively, Docling has support for other OCR engines. See the documentation."
                )

            # This configuration option will be revamped while introducing device settings for all models.
            # For the moment we will default to auto and let onnx-runtime pick the best.
            cls_use_cuda = True
            rec_use_cuda = True
            det_use_cuda = True
            det_use_dml = True
            cls_use_dml = True
            rec_use_dml = True

            # # Same as Defaults in RapidOCR
            # cls_use_cuda = False
            # rec_use_cuda = False
            # det_use_cuda = False
            # det_use_dml = False
            # cls_use_dml = False
            # rec_use_dml = False

            # # If we set everything to true onnx-runtime would automatically choose the fastest accelerator
            # if self.options.device == self.options.Device.AUTO:
            #     cls_use_cuda = True
            #     rec_use_cuda = True
            #     det_use_cuda = True
            #     det_use_dml = True
            #     cls_use_dml = True
            #     rec_use_dml = True

            # # If we set use_cuda to true onnx would use the cuda device available in runtime if no cuda device is available it would run on CPU.
            # elif self.options.device == self.options.Device.CUDA:
            #     cls_use_cuda = True
            #     rec_use_cuda = True
            #     det_use_cuda = True

            # # If we set use_dml to true onnx would use the dml device available in runtime if no dml device is available it would work on CPU.
            # elif self.options.device == self.options.Device.DIRECTML:
            #     det_use_dml = True
            #     cls_use_dml = True
            #     rec_use_dml = True

            self.reader = RapidOCR(
                text_score=self.options.text_score,
                cls_use_cuda=cls_use_cuda,
                rec_use_cuda=rec_use_cuda,
                det_use_cuda=det_use_cuda,
                det_use_dml=det_use_dml,
                cls_use_dml=cls_use_dml,
                rec_use_dml=rec_use_dml,
                print_verbose=self.options.print_verbose,
                det_model_path=self.options.det_model_path,
                cls_model_path=self.options.cls_model_path,
                rec_model_path=self.options.rec_model_path,
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
                        result, _ = self.reader(
                            im,
                            use_det=self.options.use_det,
                            use_cls=self.options.use_cls,
                            use_rec=self.options.use_rec,
                        )

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

                    # Post-process the cells
                    page.cells = self.post_process_cells(all_ocr_cells, page.cells)

                # DEBUG code:
                if settings.debug.visualize_ocr:
                    self.draw_ocr_rects_and_cells(conv_res, page, ocr_rects)

                yield page
