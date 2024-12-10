import logging
import sys
from pathlib import Path
from typing import Optional

from docling_core.types.doc import DocItem, ImageRef, PictureItem, TableItem

from docling.backend.abstract_backend import AbstractDocumentBackend
from docling.backend.pdf_backend import PdfDocumentBackend
from docling.datamodel.base_models import AssembledUnit, Page
from docling.datamodel.document import ConversionResult
from docling.datamodel.pipeline_options import (
    EasyOcrOptions,
    OcrMacOptions,
    PdfPipelineOptions,
    RapidOcrOptions,
    TesseractCliOcrOptions,
    TesseractOcrOptions,
)
from docling.models.base_ocr_model import BaseOcrModel
from docling.models.ds_glm_model import GlmModel, GlmOptions
from docling.models.easyocr_model import EasyOcrModel
from docling.models.layout_model import LayoutModel
from docling.models.ocr_mac_model import OcrMacModel
from docling.models.page_assemble_model import PageAssembleModel, PageAssembleOptions
from docling.models.page_preprocessing_model import (
    PagePreprocessingModel,
    PagePreprocessingOptions,
)
from docling.models.rapid_ocr_model import RapidOcrModel
from docling.models.table_structure_model import TableStructureModel
from docling.models.tesseract_ocr_cli_model import TesseractOcrCliModel
from docling.models.tesseract_ocr_model import TesseractOcrModel
from docling.pipeline.base_pipeline import PaginatedPipeline
from docling.utils.profiling import ProfilingScope, TimeRecorder

_log = logging.getLogger(__name__)


class StandardPdfPipeline(PaginatedPipeline):
    _layout_model_path = "model_artifacts/layout"
    _table_model_path = "model_artifacts/tableformer"

    def __init__(self, pipeline_options: PdfPipelineOptions):
        super().__init__(pipeline_options)
        self.pipeline_options: PdfPipelineOptions

        if pipeline_options.artifacts_path is None:
            self.artifacts_path = self.download_models_hf()
        else:
            self.artifacts_path = Path(pipeline_options.artifacts_path)

        keep_images = (
            self.pipeline_options.generate_page_images
            or self.pipeline_options.generate_picture_images
            or self.pipeline_options.generate_table_images
        )

        self.glm_model = GlmModel(options=GlmOptions())

        if (ocr_model := self.get_ocr_model()) is None:
            raise RuntimeError(
                f"The specified OCR kind is not supported: {pipeline_options.ocr_options.kind}."
            )

        self.build_pipe = [
            # Pre-processing
            PagePreprocessingModel(
                options=PagePreprocessingOptions(
                    images_scale=pipeline_options.images_scale
                )
            ),
            # OCR
            ocr_model,
            # Layout model
            LayoutModel(
                artifacts_path=self.artifacts_path
                / StandardPdfPipeline._layout_model_path,
                accelerator_options=pipeline_options.accelerator_options,
            ),
            # Table structure model
            TableStructureModel(
                enabled=pipeline_options.do_table_structure,
                artifacts_path=self.artifacts_path
                / StandardPdfPipeline._table_model_path,
                options=pipeline_options.table_structure_options,
                accelerator_options=pipeline_options.accelerator_options,
            ),
            # Page assemble
            PageAssembleModel(options=PageAssembleOptions(keep_images=keep_images)),
        ]

        self.enrichment_pipe = [
            # Other models working on `NodeItem` elements in the DoclingDocument
        ]

    @staticmethod
    def download_models_hf(
        local_dir: Optional[Path] = None, force: bool = False
    ) -> Path:
        from huggingface_hub import snapshot_download
        from huggingface_hub.utils import disable_progress_bars

        disable_progress_bars()
        download_path = snapshot_download(
            repo_id="ds4sd/docling-models",
            force_download=force,
            local_dir=local_dir,
            revision="v2.1.0",
        )

        return Path(download_path)

    def get_ocr_model(self) -> Optional[BaseOcrModel]:
        if isinstance(self.pipeline_options.ocr_options, EasyOcrOptions):
            return EasyOcrModel(
                enabled=self.pipeline_options.do_ocr,
                options=self.pipeline_options.ocr_options,
                accelerator_options=self.pipeline_options.accelerator_options,
            )
        elif isinstance(self.pipeline_options.ocr_options, TesseractCliOcrOptions):
            return TesseractOcrCliModel(
                enabled=self.pipeline_options.do_ocr,
                options=self.pipeline_options.ocr_options,
            )
        elif isinstance(self.pipeline_options.ocr_options, TesseractOcrOptions):
            return TesseractOcrModel(
                enabled=self.pipeline_options.do_ocr,
                options=self.pipeline_options.ocr_options,
            )
        elif isinstance(self.pipeline_options.ocr_options, RapidOcrOptions):
            return RapidOcrModel(
                enabled=self.pipeline_options.do_ocr,
                options=self.pipeline_options.ocr_options,
                accelerator_options=self.pipeline_options.accelerator_options,
            )
        elif isinstance(self.pipeline_options.ocr_options, OcrMacOptions):
            if "darwin" != sys.platform:
                raise RuntimeError(
                    f"The specified OCR type is only supported on Mac: {self.pipeline_options.ocr_options.kind}."
                )
            return OcrMacModel(
                enabled=self.pipeline_options.do_ocr,
                options=self.pipeline_options.ocr_options,
            )
        return None

    def initialize_page(self, conv_res: ConversionResult, page: Page) -> Page:
        with TimeRecorder(conv_res, "page_init"):
            page._backend = conv_res.input._backend.load_page(page.page_no)  # type: ignore
            if page._backend is not None and page._backend.is_valid():
                page.size = page._backend.get_size()

        return page

    def _assemble_document(self, conv_res: ConversionResult) -> ConversionResult:
        all_elements = []
        all_headers = []
        all_body = []

        with TimeRecorder(conv_res, "doc_assemble", scope=ProfilingScope.DOCUMENT):
            for p in conv_res.pages:
                if p.assembled is not None:
                    for el in p.assembled.body:
                        all_body.append(el)
                    for el in p.assembled.headers:
                        all_headers.append(el)
                    for el in p.assembled.elements:
                        all_elements.append(el)

            conv_res.assembled = AssembledUnit(
                elements=all_elements, headers=all_headers, body=all_body
            )

            conv_res.document = self.glm_model(conv_res)

            # Generate page images in the output
            if self.pipeline_options.generate_page_images:
                for page in conv_res.pages:
                    assert page.image is not None
                    page_no = page.page_no + 1
                    conv_res.document.pages[page_no].image = ImageRef.from_pil(
                        page.image, dpi=int(72 * self.pipeline_options.images_scale)
                    )

            # Generate images of the requested element types
            if (
                self.pipeline_options.generate_picture_images
                or self.pipeline_options.generate_table_images
            ):
                scale = self.pipeline_options.images_scale
                for element, _level in conv_res.document.iterate_items():
                    if not isinstance(element, DocItem) or len(element.prov) == 0:
                        continue
                    if (
                        isinstance(element, PictureItem)
                        and self.pipeline_options.generate_picture_images
                    ) or (
                        isinstance(element, TableItem)
                        and self.pipeline_options.generate_table_images
                    ):
                        page_ix = element.prov[0].page_no - 1
                        page = conv_res.pages[page_ix]
                        assert page.size is not None
                        assert page.image is not None

                        crop_bbox = (
                            element.prov[0]
                            .bbox.scaled(scale=scale)
                            .to_top_left_origin(page_height=page.size.height * scale)
                        )

                        cropped_im = page.image.crop(crop_bbox.as_tuple())
                        element.image = ImageRef.from_pil(
                            cropped_im, dpi=int(72 * scale)
                        )

        return conv_res

    @classmethod
    def get_default_options(cls) -> PdfPipelineOptions:
        return PdfPipelineOptions()

    @classmethod
    def is_backend_supported(cls, backend: AbstractDocumentBackend):
        return isinstance(backend, PdfDocumentBackend)
