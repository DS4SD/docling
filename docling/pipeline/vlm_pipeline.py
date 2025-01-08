import logging
from pathlib import Path
from typing import Optional

from docling_core.types import DoclingDocument
from docling_core.types.doc import DocItem, ImageRef, PictureItem, TableItem

from docling.backend.abstract_backend import AbstractDocumentBackend
from docling.backend.pdf_backend import PdfDocumentBackend
from docling.datamodel.base_models import Page
from docling.datamodel.document import ConversionResult
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.models.smol_docling_model import SmolDoclingModel
from docling.pipeline.base_pipeline import PaginatedPipeline
from docling.utils.profiling import ProfilingScope, TimeRecorder

_log = logging.getLogger(__name__)


class VlmPipeline(PaginatedPipeline):
    _smol_vlm_path = "model_artifacts/smol_vlm"  # TODO or whatever is needed.

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

        self.build_pipe = [
            SmolDoclingModel(
                artifacts_path=self.artifacts_path / VlmPipeline._smol_vlm_path,
                accelerator_options=pipeline_options.accelerator_options,
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
        from huggingface_hub.utils import disable_progress_bars

        disable_progress_bars()

        # TODO download the correct model (private repo)
        download_path = snapshot_download(
            repo_id="ds4sd/xxx",
            force_download=force,
            local_dir=local_dir,
        )

        return Path(download_path)

    def initialize_page(self, conv_res: ConversionResult, page: Page) -> Page:
        with TimeRecorder(conv_res, "page_init"):
            page._backend = conv_res.input._backend.load_page(page.page_no)  # type: ignore
            if page._backend is not None and page._backend.is_valid():
                page.size = page._backend.get_size()

        return page

    def _assemble_document(self, conv_res: ConversionResult) -> ConversionResult:
        with TimeRecorder(conv_res, "doc_assemble", scope=ProfilingScope.DOCUMENT):

            # Read and concatenate the page doctags:
            document_tags = ""
            for page in conv_res.pages:
                if page.predictions.doctags is not None:
                    document_tags += page.predictions.doctags.tag_string

            # TODO implement this function
            conv_res.document = self._turn_tags_into_doc(document_tags)

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

    def _turn_tags_into_doc(self, document_tags):
        return DoclingDocument()
