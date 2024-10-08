import logging
from pathlib import Path
from typing import Optional

from docling.backend.abstract_backend import AbstractDocumentBackend
from docling.backend.pdf_backend import PdfDocumentBackend
from docling.datamodel.base_models import AssembledUnit, Page
from docling.datamodel.document import ConversionResult, InputDocument
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.models.ds_glm_model import GlmModel
from docling.models.easyocr_model import EasyOcrModel
from docling.models.layout_model import LayoutModel
from docling.models.page_assemble_model import PageAssembleModel
from docling.models.page_preprocessing_model import PagePreprocessingModel
from docling.models.table_structure_model import TableStructureModel
from docling.pipeline.base_model_pipeline import PaginatedModelPipeline

_log = logging.getLogger(__name__)


class StandardPdfModelPipeline(PaginatedModelPipeline):
    _layout_model_path = "model_artifacts/layout/beehive_v0.0.5_pt"
    _table_model_path = "model_artifacts/tableformer"

    def __init__(self, pipeline_options: PdfPipelineOptions):
        super().__init__(pipeline_options)

        if not pipeline_options.artifacts_path:
            artifacts_path = self.download_models_hf()

        self.artifacts_path = Path(artifacts_path)
        self.glm_model = GlmModel(config={})

        self.model_pipe = [
            PagePreprocessingModel(
                config={"images_scale": pipeline_options.images_scale}
            ),
            EasyOcrModel(
                config={
                    "lang": ["fr", "de", "es", "en"],
                    "enabled": pipeline_options.do_ocr,
                }
            ),
            LayoutModel(
                config={
                    "artifacts_path": artifacts_path
                    / StandardPdfModelPipeline._layout_model_path
                }
            ),
            TableStructureModel(
                config={
                    "artifacts_path": artifacts_path
                    / StandardPdfModelPipeline._table_model_path,
                    "enabled": pipeline_options.do_table_structure,
                    "do_cell_matching": pipeline_options.table_structure_options.do_cell_matching,
                    "mode": pipeline_options.table_structure_options.mode,
                }
            ),
            PageAssembleModel(config={"images_scale": pipeline_options.images_scale}),
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
            revision="v2.0.0",
        )

        return Path(download_path)

    def initialize_page(self, doc: InputDocument, page: Page) -> Page:
        page._backend = doc._backend.load_page(page.page_no)
        page.size = page._backend.get_size()

        return page

    def assemble_document(
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

        conv_res.output, conv_res.experimental = self.glm_model(conv_res)

        return conv_res

    @classmethod
    def get_default_options(cls) -> PdfPipelineOptions:
        return PdfPipelineOptions()

    @classmethod
    def is_backend_supported(cls, backend: AbstractDocumentBackend):
        return isinstance(backend, PdfDocumentBackend)
