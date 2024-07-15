import functools
import logging
import time
import traceback
from pathlib import Path
from typing import Iterable, Optional, Type, Union

from PIL import ImageDraw

from docling.backend.abstract_backend import PdfDocumentBackend
from docling.datamodel.base_models import (
    AssembledUnit,
    ConversionStatus,
    Page,
    PipelineOptions,
)
from docling.datamodel.document import (
    ConvertedDocument,
    DocumentConversionInput,
    InputDocument,
)
from docling.datamodel.settings import settings
from docling.models.ds_glm_model import GlmModel
from docling.models.page_assemble_model import PageAssembleModel
from docling.pipeline.base_model_pipeline import BaseModelPipeline
from docling.pipeline.standard_model_pipeline import StandardModelPipeline
from docling.utils.utils import chunkify, create_hash

_log = logging.getLogger(__name__)


class DocumentConverter:
    _layout_model_path = "model_artifacts/layout/beehive_v0.0.5"
    _table_model_path = "model_artifacts/tableformer"

    def __init__(
        self,
        artifacts_path: Optional[Union[Path, str]] = None,
        pipeline_options: PipelineOptions = PipelineOptions(),
        pdf_backend: Type[PdfDocumentBackend] = DocumentConversionInput.DEFAULT_BACKEND,
        pipeline_cls: Type[BaseModelPipeline] = StandardModelPipeline,
    ):
        if not artifacts_path:
            artifacts_path = self.download_models_hf()

        artifacts_path = Path(artifacts_path)

        self.model_pipeline = pipeline_cls(
            artifacts_path=artifacts_path, pipeline_options=pipeline_options
        )

        self.page_assemble_model = PageAssembleModel(config={})
        self.glm_model = GlmModel(config={})
        self.pdf_backend = pdf_backend

    @staticmethod
    def download_models_hf(
        local_dir: Optional[Path] = None, force: bool = False
    ) -> Path:
        from huggingface_hub import snapshot_download

        download_path = snapshot_download(
            repo_id="ds4sd/docling-models", force_download=force, local_dir=local_dir
        )

        return Path(download_path)

    def convert(self, input: DocumentConversionInput) -> Iterable[ConvertedDocument]:

        for input_batch in chunkify(
            input.docs(pdf_backend=self.pdf_backend), settings.perf.doc_batch_size
        ):
            _log.info(f"Going to convert document batch...")
            # parallel processing only within input_batch
            # with ThreadPoolExecutor(
            #    max_workers=settings.perf.doc_batch_concurrency
            # ) as pool:
            #   yield from pool.map(self.process_document, input_batch)

            # Note: Pdfium backend is not thread-safe, thread pool usage was disabled.
            yield from map(self.process_document, input_batch)

    def process_document(self, in_doc: InputDocument) -> ConvertedDocument:
        start_doc_time = time.time()
        converted_doc = ConvertedDocument(input=in_doc)

        if not in_doc.valid:
            converted_doc.status = ConversionStatus.FAILURE
            return converted_doc

        for i in range(0, in_doc.page_count):
            converted_doc.pages.append(Page(page_no=i))

        all_assembled_pages = []

        try:
            # Iterate batches of pages (page_batch_size) in the doc
            for page_batch in chunkify(
                converted_doc.pages, settings.perf.page_batch_size
            ):

                start_pb_time = time.time()
                # Pipeline

                # 1. Initialise the page resources
                init_pages = map(
                    functools.partial(self.initialize_page, in_doc), page_batch
                )

                # 2. Populate page image
                pages_with_images = map(
                    functools.partial(self.populate_page_images, in_doc), init_pages
                )

                # 3. Populate programmatic page cells
                pages_with_cells = map(
                    functools.partial(self.parse_page_cells, in_doc),
                    pages_with_images,
                )

                pipeline_pages = self.model_pipeline.apply(pages_with_cells)

                # 7. Assemble page elements (per page)
                assembled_pages = self.page_assemble_model(pipeline_pages)

                # exhaust assembled_pages
                for assembled_page in assembled_pages:
                    # Free up mem resources before moving on with next batch
                    assembled_page.image = (
                        None  # Comment this if you want to visualize page images
                    )
                    assembled_page._backend.unload()

                    all_assembled_pages.append(assembled_page)

                end_pb_time = time.time() - start_pb_time
                _log.info(f"Finished converting page batch time={end_pb_time:.3f}")

            # Free up mem resources of PDF backend
            in_doc._backend.unload()

            converted_doc.pages = all_assembled_pages
            self.assemble_doc(converted_doc)

            converted_doc.status = ConversionStatus.SUCCESS

        except Exception as e:
            converted_doc.status = ConversionStatus.FAILURE
            trace = "\n".join(traceback.format_exception(e))
            _log.info(f"Encountered an error during conversion: {trace}")

        end_doc_time = time.time() - start_doc_time
        _log.info(
            f"Finished converting document time-pages={end_doc_time:.2f}/{in_doc.page_count}"
        )

        return converted_doc

    # Initialise and load resources for a page, before downstream steps (populate images, cells, ...)
    def initialize_page(self, doc: InputDocument, page: Page) -> Page:
        page._backend = doc._backend.load_page(page.page_no)
        page.size = page._backend.get_size()
        page.page_hash = create_hash(doc.document_hash + ":" + str(page.page_no))

        return page

    # Generate the page image and store it in the page object
    def populate_page_images(self, doc: InputDocument, page: Page) -> Page:
        page.image = page._backend.get_page_image()

        return page

    # Extract and populate the page cells and store it in the page object
    def parse_page_cells(self, doc: InputDocument, page: Page) -> Page:
        page.cells = page._backend.get_text_cells()

        # DEBUG code:
        def draw_text_boxes(image, cells):
            draw = ImageDraw.Draw(image)
            for c in cells:
                x0, y0, x1, y1 = c.bbox.as_tuple()
                draw.rectangle([(x0, y0), (x1, y1)], outline="red")
            image.show()

        # draw_text_boxes(page.image, cells)

        return page

    def assemble_doc(self, converted_doc: ConvertedDocument):
        all_elements = []
        all_headers = []
        all_body = []

        for p in converted_doc.pages:

            for el in p.assembled.body:
                all_body.append(el)
            for el in p.assembled.headers:
                all_headers.append(el)
            for el in p.assembled.elements:
                all_elements.append(el)

        converted_doc.assembled = AssembledUnit(
            elements=all_elements, headers=all_headers, body=all_body
        )

        converted_doc.output = self.glm_model(converted_doc)
