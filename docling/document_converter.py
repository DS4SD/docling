import functools
import logging
import tempfile
import time
import traceback
from pathlib import Path
from typing import Iterable, Optional, Type, Union

import requests
from PIL import ImageDraw
from pydantic import AnyHttpUrl, TypeAdapter, ValidationError

from docling.backend.abstract_backend import PdfDocumentBackend
from docling.datamodel.base_models import (
    AssembledUnit,
    AssembleOptions,
    ConversionStatus,
    DoclingComponentType,
    ErrorItem,
    Page,
)
from docling.datamodel.document import (
    ConversionResult,
    DocumentConversionInput,
    InputDocument,
)
from docling.datamodel.pipeline_options import PipelineOptions
from docling.datamodel.settings import settings
from docling.models.ds_glm_model import GlmModel
from docling.models.page_assemble_model import PageAssembleModel
from docling.pipeline.base_model_pipeline import BaseModelPipeline
from docling.pipeline.standard_model_pipeline import StandardModelPipeline
from docling.utils.utils import chunkify, create_hash

_log = logging.getLogger(__name__)


class DocumentConverter:
    _default_download_filename = "file.pdf"

    def __init__(
        self,
        artifacts_path: Optional[Union[Path, str]] = None,
        pipeline_options: PipelineOptions = PipelineOptions(),
        pdf_backend: Type[PdfDocumentBackend] = DocumentConversionInput.DEFAULT_BACKEND,
        pipeline_cls: Type[BaseModelPipeline] = StandardModelPipeline,
        assemble_options: AssembleOptions = AssembleOptions(),
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
        self.assemble_options = assemble_options

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

    def convert(self, input: DocumentConversionInput) -> Iterable[ConversionResult]:

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
            yield from map(self._process_document, input_batch)

    def convert_single(self, source: Path | AnyHttpUrl | str) -> ConversionResult:
        """Convert a single document.

        Args:
            source (Path | AnyHttpUrl | str): The PDF input source. Can be a path or URL.

        Raises:
            ValueError: If source is of unexpected type.
            RuntimeError: If conversion fails.

        Returns:
            ConversionResult: The conversion result object.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                http_url: AnyHttpUrl = TypeAdapter(AnyHttpUrl).validate_python(source)
                res = requests.get(http_url, stream=True)
                res.raise_for_status()
                fname = None
                # try to get filename from response header
                if cont_disp := res.headers.get("Content-Disposition"):
                    for par in cont_disp.strip().split(";"):
                        # currently only handling directive "filename" (not "*filename")
                        if (split := par.split("=")) and split[0].strip() == "filename":
                            fname = "=".join(split[1:]).strip().strip("'\"") or None
                            break
                # otherwise, use name from URL:
                if fname is None:
                    fname = Path(http_url.path).name or self._default_download_filename
                local_path = Path(temp_dir) / fname
                with open(local_path, "wb") as f:
                    for chunk in res.iter_content(chunk_size=1024):  # using 1-KB chunks
                        f.write(chunk)
            except ValidationError:
                try:
                    local_path = TypeAdapter(Path).validate_python(source)
                except ValidationError:
                    raise ValueError(
                        f"Unexpected file path type encountered: {type(source)}"
                    )
            conv_inp = DocumentConversionInput.from_paths(paths=[local_path])
            conv_res_iter = self.convert(conv_inp)
            conv_res: ConversionResult = next(conv_res_iter)
        if conv_res.status not in {
            ConversionStatus.SUCCESS,
            ConversionStatus.PARTIAL_SUCCESS,
        }:
            raise RuntimeError(f"Conversion failed with status: {conv_res.status}")
        return conv_res

    def _process_document(self, in_doc: InputDocument) -> ConversionResult:
        start_doc_time = time.time()
        conv_res = ConversionResult(input=in_doc)

        _log.info(f"Processing document {in_doc.file.name}")

        if not in_doc.valid:
            conv_res.status = ConversionStatus.FAILURE
            return conv_res

        for i in range(0, in_doc.page_count):
            conv_res.pages.append(Page(page_no=i))

        all_assembled_pages = []

        try:
            # Iterate batches of pages (page_batch_size) in the doc
            for page_batch in chunkify(conv_res.pages, settings.perf.page_batch_size):
                start_pb_time = time.time()
                # Pipeline

                # 1. Initialise the page resources
                init_pages = map(
                    functools.partial(self._initialize_page, in_doc), page_batch
                )

                # 2. Populate page image
                pages_with_images = map(
                    functools.partial(self._populate_page_images, in_doc), init_pages
                )

                # 3. Populate programmatic page cells
                pages_with_cells = map(
                    functools.partial(self._parse_page_cells, in_doc),
                    pages_with_images,
                )

                # 4. Run pipeline stages
                pipeline_pages = self.model_pipeline.apply(pages_with_cells)

                # 5. Assemble page elements (per page)
                assembled_pages = self.page_assemble_model(pipeline_pages)

                # exhaust assembled_pages
                for assembled_page in assembled_pages:
                    # Free up mem resources before moving on with next batch

                    # Remove page images (can be disabled)
                    if self.assemble_options.images_scale is None:
                        assembled_page._image_cache = {}

                    # Unload backend
                    assembled_page._backend.unload()

                    all_assembled_pages.append(assembled_page)

                end_pb_time = time.time() - start_pb_time
                _log.info(f"Finished converting page batch time={end_pb_time:.3f}")

            conv_res.pages = all_assembled_pages
            self._assemble_doc(conv_res)

            status = ConversionStatus.SUCCESS
            for page in conv_res.pages:
                if not page._backend.is_valid():
                    conv_res.errors.append(
                        ErrorItem(
                            component_type=DoclingComponentType.PDF_BACKEND,
                            module_name=type(page._backend).__name__,
                            error_message=f"Page {page.page_no} failed to parse.",
                        )
                    )
                    status = ConversionStatus.PARTIAL_SUCCESS

            conv_res.status = status

        except Exception as e:
            conv_res.status = ConversionStatus.FAILURE
            trace = "\n".join(traceback.format_exception(e))
            _log.info(
                f"Encountered an error during conversion of document {in_doc.document_hash}:\n"
                f"{trace}"
            )

        finally:
            # Always unload the PDF backend, even in case of failure
            if in_doc._backend:
                in_doc._backend.unload()

        end_doc_time = time.time() - start_doc_time
        _log.info(
            f"Finished converting document time-pages={end_doc_time:.2f}/{in_doc.page_count}"
        )

        return conv_res

    # Initialise and load resources for a page, before downstream steps (populate images, cells, ...)
    def _initialize_page(self, doc: InputDocument, page: Page) -> Page:
        page._backend = doc._backend.load_page(page.page_no)
        page.size = page._backend.get_size()
        page.page_hash = create_hash(doc.document_hash + ":" + str(page.page_no))

        return page

    # Generate the page image and store it in the page object
    def _populate_page_images(self, doc: InputDocument, page: Page) -> Page:
        # default scale
        page.get_image(
            scale=1.0
        )  # puts the page image on the image cache at default scale

        # user requested scales
        if self.assemble_options.images_scale is not None:
            page._default_image_scale = self.assemble_options.images_scale
            page.get_image(
                scale=self.assemble_options.images_scale
            )  # this will trigger storing the image in the internal cache

        return page

    # Extract and populate the page cells and store it in the page object
    def _parse_page_cells(self, doc: InputDocument, page: Page) -> Page:
        page.cells = page._backend.get_text_cells()

        # DEBUG code:
        def draw_text_boxes(image, cells):
            draw = ImageDraw.Draw(image)
            for c in cells:
                x0, y0, x1, y1 = c.bbox.as_tuple()
                draw.rectangle([(x0, y0), (x1, y1)], outline="red")
            image.show()

        # draw_text_boxes(page.get_image(scale=1.0), cells)

        return page

    def _assemble_doc(self, conv_res: ConversionResult):
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

        conv_res.output = self.glm_model(conv_res)
