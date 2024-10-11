import functools
import logging
import time
import traceback
from abc import ABC, abstractmethod
from typing import Callable, Iterable, List

from docling.backend.abstract_backend import AbstractDocumentBackend
from docling.backend.pdf_backend import PdfDocumentBackend
from docling.datamodel.base_models import (
    ConversionStatus,
    DoclingComponentType,
    ErrorItem,
    Page,
)
from docling.datamodel.document import ConversionResult, InputDocument
from docling.datamodel.pipeline_options import PipelineOptions
from docling.datamodel.settings import settings
from docling.utils.utils import chunkify

_log = logging.getLogger(__name__)


class AbstractModelPipeline(ABC):
    def __init__(self, pipeline_options: PipelineOptions):
        self.pipeline_options = pipeline_options
        self.model_pipe: List[Callable] = []
        self.enrichment_pipe: List[Callable] = []

    def execute(self, in_doc: InputDocument) -> ConversionResult:
        conv_res = ConversionResult(input=in_doc)

        _log.info(f"Processing document {in_doc.file.name}")

        if not in_doc.valid:
            conv_res.status = ConversionStatus.FAILURE
            return conv_res

        # TODO: propagate option for raises_on_error?
        try:
            conv_res = self._build_document(in_doc, conv_res)
            conv_res = self._assemble_document(in_doc, conv_res)
            conv_res = self._enrich_document(in_doc, conv_res)
            conv_res.status = self._determine_status(in_doc, conv_res)
        except Exception as e:
            conv_res.status = ConversionStatus.FAILURE

        return conv_res

    @abstractmethod
    def _build_document(
        self, in_doc: InputDocument, conv_res: ConversionResult
    ) -> ConversionResult:
        pass

    def _assemble_document(
        self, in_doc: InputDocument, conv_res: ConversionResult
    ) -> ConversionResult:
        return conv_res

    def _enrich_document(
        self, in_doc: InputDocument, conv_res: ConversionResult
    ) -> ConversionResult:
        return conv_res

    @abstractmethod
    def _determine_status(
        self, in_doc: InputDocument, conv_res: ConversionResult
    ) -> ConversionStatus:
        pass

    @classmethod
    @abstractmethod
    def get_default_options(cls) -> PipelineOptions:
        pass

    @classmethod
    @abstractmethod
    def is_backend_supported(cls, backend: AbstractDocumentBackend):
        pass

    # def _apply_on_elements(self, element_batch: Iterable[NodeItem]) -> Iterable[Any]:
    #    for model in self.model_pipe:
    #        element_batch = model(element_batch)
    #
    #    yield from element_batch


class PaginatedModelPipeline(AbstractModelPipeline):  # TODO this is a bad name.

    def _apply_on_pages(self, page_batch: Iterable[Page]) -> Iterable[Page]:
        for model in self.model_pipe:
            page_batch = model(page_batch)

        yield from page_batch

    def _build_document(
        self, in_doc: InputDocument, conv_res: ConversionResult
    ) -> ConversionResult:

        if not isinstance(in_doc._backend, PdfDocumentBackend):
            raise RuntimeError(
                f"The selected backend {type(in_doc._backend).__name__} for {in_doc.file} is not a PDF backend. "
                f"Can not convert this with a PDF pipeline. "
                f"Please check your format configuration on DocumentConverter."
            )
            # conv_res.status = ConversionStatus.FAILURE
            # return conv_res

        for i in range(0, in_doc.page_count):
            conv_res.pages.append(Page(page_no=i))

        try:
            # Iterate batches of pages (page_batch_size) in the doc
            for page_batch in chunkify(conv_res.pages, settings.perf.page_batch_size):
                start_pb_time = time.time()

                # 1. Initialise the page resources
                init_pages = map(
                    functools.partial(self.initialize_page, in_doc), page_batch
                )

                # 2. Run pipeline stages
                pipeline_pages = self._apply_on_pages(init_pages)

                for p in pipeline_pages:  # Must exhaust!
                    pass

                end_pb_time = time.time() - start_pb_time
                _log.info(f"Finished converting page batch time={end_pb_time:.3f}")

        except Exception as e:
            conv_res.status = ConversionStatus.FAILURE
            trace = "\n".join(traceback.format_exception(e))
            _log.warning(
                f"Encountered an error during conversion of document {in_doc.document_hash}:\n"
                f"{trace}"
            )
            # raise e  # TODO Debug, should not be here.
        finally:
            # Always unload the PDF backend, even in case of failure
            if in_doc._backend:
                in_doc._backend.unload()

        return conv_res

    def _determine_status(
        self, in_doc: InputDocument, conv_res: ConversionResult
    ) -> ConversionStatus:
        status = ConversionStatus.SUCCESS
        for page in conv_res.pages:
            if not page._backend.is_valid():
                conv_res.errors.append(
                    ErrorItem(
                        component_type=DoclingComponentType.DOCUMENT_BACKEND,
                        module_name=type(page._backend).__name__,
                        error_message=f"Page {page.page_no} failed to parse.",
                    )
                )
                status = ConversionStatus.PARTIAL_SUCCESS

        return status

    # Initialise and load resources for a page
    @abstractmethod
    def initialize_page(self, doc: InputDocument, page: Page) -> Page:
        pass
