import logging

from docling.backend.abstract_backend import (
    AbstractDocumentBackend,
    DeclarativeDocumentBackend,
)
from docling.datamodel.base_models import ConversionStatus
from docling.datamodel.document import ConversionResult, InputDocument
from docling.datamodel.pipeline_options import PipelineOptions
from docling.pipeline.base_model_pipeline import AbstractModelPipeline

_log = logging.getLogger(__name__)


class SimpleModelPipeline(AbstractModelPipeline):
    """SimpleModelPipeline.

    This class is used at the moment for formats / backends
    which produce straight DoclingDocument output.
    """

    def __init__(self, pipeline_options: PipelineOptions):
        super().__init__(pipeline_options)

    def execute(self, in_doc: InputDocument) -> ConversionResult:
        conv_res = ConversionResult(input=in_doc)

        _log.info(f"Processing document {in_doc.file.name}")

        if not in_doc.valid:
            conv_res.status = ConversionStatus.FAILURE
            return conv_res

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

        conv_res.output = in_doc._backend.convert()
        # Do other stuff with conv_res.experimental

        conv_res = self._assemble_document(in_doc, conv_res)

        conv_res.status = ConversionStatus.SUCCESS

        return conv_res

    # def _apply_on_elements(self, element_batch: Iterable[NodeItem]) -> Iterable[Any]:
    #    for model in self.model_pipe:
    #        element_batch = model(element_batch)
    #
    #    yield from element_batch

    def _assemble_document(
        self, in_doc: InputDocument, conv_res: ConversionResult
    ) -> ConversionResult:
        return conv_res

    @classmethod
    def get_default_options(cls) -> PipelineOptions:
        return PipelineOptions()

    @classmethod
    def is_backend_supported(cls, backend: AbstractDocumentBackend):
        return isinstance(backend, DeclarativeDocumentBackend)
