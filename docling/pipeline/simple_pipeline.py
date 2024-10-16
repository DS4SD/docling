import logging

from docling.backend.abstract_backend import (
    AbstractDocumentBackend,
    DeclarativeDocumentBackend,
)
from docling.datamodel.base_models import ConversionStatus
from docling.datamodel.document import ConversionResult, InputDocument
from docling.datamodel.pipeline_options import PipelineOptions
from docling.pipeline.base_pipeline import BasePipeline

_log = logging.getLogger(__name__)


class SimplePipeline(BasePipeline):
    """SimpleModelPipeline.

    This class is used at the moment for formats / backends
    which produce straight DoclingDocument output.
    """

    def __init__(self, pipeline_options: PipelineOptions):
        super().__init__(pipeline_options)

    def _build_document(
        self, in_doc: InputDocument, conv_res: ConversionResult
    ) -> ConversionResult:

        if not isinstance(in_doc._backend, DeclarativeDocumentBackend):
            raise RuntimeError(
                f"The selected backend {type(in_doc._backend).__name__} for {in_doc.file} is not a declarative backend. "
                f"Can not convert this with simple pipeline. "
                f"Please check your format configuration on DocumentConverter."
            )
            # conv_res.status = ConversionStatus.FAILURE
            # return conv_res

        # Instead of running a page-level pipeline to build up the document structure,
        # the backend is expected to be of type DeclarativeDocumentBackend, which can output
        # a DoclingDocument straight.

        conv_res.document = in_doc._backend.convert()
        return conv_res

    def _determine_status(
        self, in_doc: InputDocument, conv_res: ConversionResult
    ) -> ConversionStatus:
        # This is called only if the previous steps didn't raise.
        # Since we don't have anything else to evaluate, we can
        # safely return SUCCESS.
        return ConversionStatus.SUCCESS

    @classmethod
    def get_default_options(cls) -> PipelineOptions:
        return PipelineOptions()

    @classmethod
    def is_backend_supported(cls, backend: AbstractDocumentBackend):
        return isinstance(backend, DeclarativeDocumentBackend)
