import logging
import warnings
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Union, cast

# from docling_core.types import DoclingDocument
from docling_core.types.doc import BoundingBox, DocItem, ImageRef, PictureItem, TextItem
from docling_core.types.doc.document import DocTagsDocument
from PIL import Image as PILImage

from docling.backend.abstract_backend import AbstractDocumentBackend
from docling.backend.md_backend import MarkdownDocumentBackend
from docling.backend.pdf_backend import PdfDocumentBackend
from docling.datamodel.base_models import InputFormat, Page
from docling.datamodel.document import ConversionResult, InputDocument
from docling.datamodel.pipeline_options import ResponseFormat, VlmPipelineOptions
from docling.datamodel.settings import settings
from docling.models.hf_vlm_model import HuggingFaceVlmModel
from docling.pipeline.base_pipeline import PaginatedPipeline
from docling.utils.profiling import ProfilingScope, TimeRecorder

_log = logging.getLogger(__name__)


class VlmPipeline(PaginatedPipeline):

    def __init__(self, pipeline_options: VlmPipelineOptions):
        super().__init__(pipeline_options)
        self.keep_backend = True

        warnings.warn(
            "The VlmPipeline is currently experimental and may change in upcoming versions without notice.",
            category=UserWarning,
            stacklevel=2,
        )

        self.pipeline_options: VlmPipelineOptions

        artifacts_path: Optional[Path] = None
        if pipeline_options.artifacts_path is not None:
            artifacts_path = Path(pipeline_options.artifacts_path).expanduser()
        elif settings.artifacts_path is not None:
            artifacts_path = Path(settings.artifacts_path).expanduser()

        if artifacts_path is not None and not artifacts_path.is_dir():
            raise RuntimeError(
                f"The value of {artifacts_path=} is not valid. "
                "When defined, it must point to a folder containing all models required by the pipeline."
            )

        # force_backend_text = False - use text that is coming from VLM response
        # force_backend_text = True - get text from backend using bounding boxes predicted by SmolDocling doctags
        self.force_backend_text = (
            pipeline_options.force_backend_text
            and pipeline_options.vlm_options.response_format == ResponseFormat.DOCTAGS
        )

        self.keep_images = self.pipeline_options.generate_page_images

        self.build_pipe = [
            HuggingFaceVlmModel(
                enabled=True,  # must be always enabled for this pipeline to make sense.
                artifacts_path=artifacts_path,
                accelerator_options=pipeline_options.accelerator_options,
                vlm_options=self.pipeline_options.vlm_options,
            ),
        ]

        self.enrichment_pipe = [
            # Other models working on `NodeItem` elements in the DoclingDocument
        ]

    def initialize_page(self, conv_res: ConversionResult, page: Page) -> Page:
        with TimeRecorder(conv_res, "page_init"):
            page._backend = conv_res.input._backend.load_page(page.page_no)  # type: ignore
            if page._backend is not None and page._backend.is_valid():
                page.size = page._backend.get_size()

        return page

    def extract_text_from_backend(self, page: Page, bbox: BoundingBox | None) -> str:
        # Convert bounding box normalized to 0-100 into page coordinates for cropping
        text = ""
        if bbox:
            if page.size:
                if page._backend:
                    text = page._backend.get_text_in_rect(bbox)
        return text

    def _assemble_document(self, conv_res: ConversionResult) -> ConversionResult:
        with TimeRecorder(conv_res, "doc_assemble", scope=ProfilingScope.DOCUMENT):

            if (
                self.pipeline_options.vlm_options.response_format
                == ResponseFormat.DOCTAGS
            ):
                doctags_list = []
                image_list = []
                for page in conv_res.pages:
                    predicted_doctags = ""
                    img = PILImage.new("RGB", (1, 1), "rgb(255,255,255)")
                    if page.predictions.vlm_response:
                        predicted_doctags = page.predictions.vlm_response.text
                    if page.image:
                        img = page.image
                    image_list.append(img)
                    doctags_list.append(predicted_doctags)

                doctags_list_c = cast(List[Union[Path, str]], doctags_list)
                image_list_c = cast(List[Union[Path, PILImage.Image]], image_list)
                doctags_doc = DocTagsDocument.from_doctags_and_image_pairs(
                    doctags_list_c, image_list_c
                )
                conv_res.document.load_from_doctags(doctags_doc)

                # If forced backend text, replace model predicted text with backend one
                if page.size:
                    if self.force_backend_text:
                        scale = self.pipeline_options.images_scale
                        for element, _level in conv_res.document.iterate_items():
                            if (
                                not isinstance(element, TextItem)
                                or len(element.prov) == 0
                            ):
                                continue
                            crop_bbox = (
                                element.prov[0]
                                .bbox.scaled(scale=scale)
                                .to_top_left_origin(
                                    page_height=page.size.height * scale
                                )
                            )
                            txt = self.extract_text_from_backend(page, crop_bbox)
                            element.text = txt
                            element.orig = txt
            elif (
                self.pipeline_options.vlm_options.response_format
                == ResponseFormat.MARKDOWN
            ):
                conv_res.document = self._turn_md_into_doc(conv_res)

            else:
                raise RuntimeError(
                    f"Unsupported VLM response format {self.pipeline_options.vlm_options.response_format}"
                )

            # Generate images of the requested element types
            if self.pipeline_options.generate_picture_images:
                scale = self.pipeline_options.images_scale
                for element, _level in conv_res.document.iterate_items():
                    if not isinstance(element, DocItem) or len(element.prov) == 0:
                        continue
                    if (
                        isinstance(element, PictureItem)
                        and self.pipeline_options.generate_picture_images
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

    def _turn_md_into_doc(self, conv_res):
        predicted_text = ""
        for pg_idx, page in enumerate(conv_res.pages):
            if page.predictions.vlm_response:
                predicted_text += page.predictions.vlm_response.text + "\n\n"
        response_bytes = BytesIO(predicted_text.encode("utf8"))
        out_doc = InputDocument(
            path_or_stream=response_bytes,
            filename=conv_res.input.file.name,
            format=InputFormat.MD,
            backend=MarkdownDocumentBackend,
        )
        backend = MarkdownDocumentBackend(
            in_doc=out_doc,
            path_or_stream=response_bytes,
        )
        return backend.convert()

    @classmethod
    def get_default_options(cls) -> VlmPipelineOptions:
        return VlmPipelineOptions()

    @classmethod
    def is_backend_supported(cls, backend: AbstractDocumentBackend):
        return isinstance(backend, PdfDocumentBackend)
