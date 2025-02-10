import logging
import sys
import warnings
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
    PictureDescriptionApiOptions,
    PictureDescriptionVlmOptions,
    RapidOcrOptions,
    TesseractCliOcrOptions,
    TesseractOcrOptions,
)
from docling.datamodel.settings import settings
from docling.models.base_ocr_model import BaseOcrModel
from docling.models.code_formula_model import CodeFormulaModel, CodeFormulaModelOptions
from docling.models.document_picture_classifier import (
    DocumentPictureClassifier,
    DocumentPictureClassifierOptions,
)
from docling.models.ds_glm_model import GlmModel, GlmOptions
from docling.models.easyocr_model import EasyOcrModel
from docling.models.layout_model import LayoutModel
from docling.models.ocr_mac_model import OcrMacModel
from docling.models.page_assemble_model import PageAssembleModel, PageAssembleOptions
from docling.models.page_preprocessing_model import (
    PagePreprocessingModel,
    PagePreprocessingOptions,
)
from docling.models.picture_description_api_model import PictureDescriptionApiModel
from docling.models.picture_description_base_model import PictureDescriptionBaseModel
from docling.models.picture_description_vlm_model import PictureDescriptionVlmModel
from docling.models.rapid_ocr_model import RapidOcrModel
from docling.models.table_structure_model import TableStructureModel
from docling.models.tesseract_ocr_cli_model import TesseractOcrCliModel
from docling.models.tesseract_ocr_model import TesseractOcrModel
from docling.pipeline.base_pipeline import PaginatedPipeline
from docling.utils.model_downloader import download_models
from docling.utils.profiling import ProfilingScope, TimeRecorder

_log = logging.getLogger(__name__)


class StandardPdfPipeline(PaginatedPipeline):
    _layout_model_path = LayoutModel._model_path
    _table_model_path = TableStructureModel._model_path

    def __init__(self, pipeline_options: PdfPipelineOptions):
        super().__init__(pipeline_options)
        self.pipeline_options: PdfPipelineOptions

        artifacts_path: Optional[Path] = None
        if pipeline_options.artifacts_path is not None:
            artifacts_path = Path(pipeline_options.artifacts_path).expanduser()

        self.keep_images = (
            self.pipeline_options.generate_page_images
            or self.pipeline_options.generate_picture_images
            or self.pipeline_options.generate_table_images
        )

        self.glm_model = GlmModel(options=GlmOptions())

        if (ocr_model := self.get_ocr_model(artifacts_path=artifacts_path)) is None:
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
                artifacts_path=artifacts_path,
                accelerator_options=pipeline_options.accelerator_options,
            ),
            # Table structure model
            TableStructureModel(
                enabled=pipeline_options.do_table_structure,
                artifacts_path=artifacts_path,
                options=pipeline_options.table_structure_options,
                accelerator_options=pipeline_options.accelerator_options,
            ),
            # Page assemble
            PageAssembleModel(options=PageAssembleOptions()),
        ]

        # Picture description model
        if (
            picture_description_model := self.get_picture_description_model(
                artifacts_path=artifacts_path
            )
        ) is None:
            raise RuntimeError(
                f"The specified picture description kind is not supported: {pipeline_options.picture_description_options.kind}."
            )

        self.enrichment_pipe = [
            # Code Formula Enrichment Model
            CodeFormulaModel(
                enabled=pipeline_options.do_code_enrichment
                or pipeline_options.do_formula_enrichment,
                artifacts_path=artifacts_path,
                options=CodeFormulaModelOptions(
                    do_code_enrichment=pipeline_options.do_code_enrichment,
                    do_formula_enrichment=pipeline_options.do_formula_enrichment,
                ),
                accelerator_options=pipeline_options.accelerator_options,
            ),
            # Document Picture Classifier
            DocumentPictureClassifier(
                enabled=pipeline_options.do_picture_classification,
                artifacts_path=artifacts_path,
                options=DocumentPictureClassifierOptions(),
                accelerator_options=pipeline_options.accelerator_options,
            ),
            # Document Picture description
            picture_description_model,
        ]

        if (
            self.pipeline_options.do_formula_enrichment
            or self.pipeline_options.do_code_enrichment
            or self.pipeline_options.do_picture_description
        ):
            self.keep_backend = True

    @staticmethod
    def download_models_hf(
        local_dir: Optional[Path] = None, force: bool = False
    ) -> Path:
        warnings.warn(
            "The usage of StandardPdfPipeline.download_models_hf() is deprecated "
            "use instead the utility `docling-tools models download`, or "
            "the upstream method docling.utils.models_downloader.download_all()",
            DeprecationWarning,
            stacklevel=3,
        )

        output_dir = download_models(output_dir=local_dir, force=force, progress=False)
        return output_dir

    def get_ocr_model(
        self, artifacts_path: Optional[Path] = None
    ) -> Optional[BaseOcrModel]:
        if isinstance(self.pipeline_options.ocr_options, EasyOcrOptions):
            return EasyOcrModel(
                enabled=self.pipeline_options.do_ocr,
                artifacts_path=artifacts_path,
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

    def get_picture_description_model(
        self, artifacts_path: Optional[Path] = None
    ) -> Optional[PictureDescriptionBaseModel]:
        if isinstance(
            self.pipeline_options.picture_description_options,
            PictureDescriptionApiOptions,
        ):
            return PictureDescriptionApiModel(
                enabled=self.pipeline_options.do_picture_description,
                options=self.pipeline_options.picture_description_options,
            )
        elif isinstance(
            self.pipeline_options.picture_description_options,
            PictureDescriptionVlmOptions,
        ):
            return PictureDescriptionVlmModel(
                enabled=self.pipeline_options.do_picture_description,
                artifacts_path=artifacts_path,
                options=self.pipeline_options.picture_description_options,
                accelerator_options=self.pipeline_options.accelerator_options,
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
