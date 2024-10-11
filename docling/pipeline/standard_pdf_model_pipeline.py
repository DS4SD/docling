import logging
from pathlib import Path
from typing import Optional

from docling.backend.abstract_backend import AbstractDocumentBackend
from docling.backend.pdf_backend import PdfDocumentBackend
from docling.datamodel.base_models import AssembledUnit, Page
from docling.datamodel.document import ConversionResult, InputDocument
from docling.datamodel.pipeline_options import (
    EasyOcrOptions,
    PdfPipelineOptions,
    TesseractCliOcrOptions,
    TesseractOcrOptions,
)
from docling.models.base_ocr_model import BaseOcrModel
from docling.models.ds_glm_model import GlmModel, GlmOptions
from docling.models.easyocr_model import EasyOcrModel
from docling.models.layout_model import LayoutModel
from docling.models.page_assemble_model import PageAssembleModel, PageAssembleOptions
from docling.models.page_preprocessing_model import (
    PagePreprocessingModel,
    PagePreprocessingOptions,
)
from docling.models.table_structure_model import TableStructureModel
from docling.models.tesseract_ocr_cli_model import TesseractOcrCliModel
from docling.models.tesseract_ocr_model import TesseractOcrModel
from docling.pipeline.base_model_pipeline import PaginatedModelPipeline

_log = logging.getLogger(__name__)


class StandardPdfModelPipeline(PaginatedModelPipeline):
    _layout_model_path = "model_artifacts/layout/beehive_v0.0.5_pt"
    _table_model_path = "model_artifacts/tableformer"

    def __init__(self, pipeline_options: PdfPipelineOptions):
        super().__init__(pipeline_options)
        self.pipeline_options: PdfPipelineOptions

        if not pipeline_options.artifacts_path:
            artifacts_path = self.download_models_hf()

        self.artifacts_path = Path(artifacts_path)
        self.glm_model = GlmModel(
            options=GlmOptions(
                create_legacy_output=pipeline_options.create_legacy_output
            )
        )

        if ocr_model := self.get_ocr_model() is None:
            raise RuntimeError(
                f"The specified OCR kind is not supported: {pipeline_options.ocr_options.kind}."
            )

        self.model_pipe = [
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
                artifacts_path=artifacts_path
                / StandardPdfModelPipeline._layout_model_path
            ),
            # Table structure model
            TableStructureModel(
                enabled=pipeline_options.do_table_structure,
                artifacts_path=artifacts_path
                / StandardPdfModelPipeline._table_model_path,
                options=pipeline_options.table_structure_options,
            ),
            # Page assemble
            PageAssembleModel(
                options=PageAssembleOptions(
                    keep_images=pipeline_options.images_scale is not None
                )
            ),
        ]

        self.enrichment_pipe = [
            # Other models working on `NodeItem` elements in the DoclingDocument
        ]

    @staticmethod
    def download_models_hf(
        local_dir: Optional[Path] = None, force: bool = False
    ) -> Path:
        from huggingface_hub import snapshot_download

        download_path = snapshot_download(
            repo_id="ds4sd/docling-models",
            force_download=force,
            local_dir=local_dir,
            revision="v2.0.1",
        )

        return Path(download_path)

    def get_ocr_model(self) -> Optional[BaseOcrModel]:
        if isinstance(self.pipeline_options.ocr_options, EasyOcrOptions):
            return EasyOcrModel(
                enabled=self.pipeline_options.do_ocr,
                options=self.pipeline_options.ocr_options,
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
        return None

    def initialize_page(self, doc: InputDocument, page: Page) -> Page:
        page._backend = doc._backend.load_page(page.page_no)
        page.size = page._backend.get_size()

        return page

    def _assemble_document(
        self, in_doc: InputDocument, conv_res: ConversionResult
    ) -> ConversionResult:
        all_elements = []
        all_headers = []
        all_body = []

        for p in conv_res.pages:

            for el in p.assembled.body:
                all_body.append(el)
            for el in p.assembled.headers:
                all_headers.append(el)
            for el in p.assembled.elements:
                all_elements.append(el)

        conv_res.assembled = AssembledUnit(
            elements=all_elements, headers=all_headers, body=all_body
        )

        conv_res.output, conv_res.legacy_output = self.glm_model(conv_res)

        return conv_res

    @classmethod
    def get_default_options(cls) -> PdfPipelineOptions:
        return PdfPipelineOptions()

    @classmethod
    def is_backend_supported(cls, backend: AbstractDocumentBackend):
        return isinstance(backend, PdfDocumentBackend)
