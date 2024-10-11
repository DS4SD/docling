import logging
import tempfile
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Type

import requests
from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    TypeAdapter,
    ValidationError,
    model_validator,
)
from typing_extensions import deprecated

from docling.backend.abstract_backend import AbstractDocumentBackend
from docling.backend.docling_parse_backend import DoclingParseDocumentBackend
from docling.backend.html_backend import HTMLDocumentBackend
from docling.backend.mspowerpoint_backend import MsPowerpointDocumentBackend
from docling.backend.msword_backend import MsWordDocumentBackend
from docling.datamodel.base_models import ConversionStatus, InputFormat
from docling.datamodel.document import (
    ConversionResult,
    DocumentConversionInput,
    InputDocument,
)
from docling.datamodel.pipeline_options import PipelineOptions
from docling.datamodel.settings import settings
from docling.pipeline.base_model_pipeline import AbstractModelPipeline
from docling.pipeline.simple_model_pipeline import SimpleModelPipeline
from docling.pipeline.standard_pdf_model_pipeline import StandardPdfModelPipeline
from docling.utils.utils import chunkify

_log = logging.getLogger(__name__)


class FormatOption(BaseModel):
    pipeline_cls: Type[AbstractModelPipeline]
    pipeline_options: Optional[PipelineOptions] = None
    backend: Type[AbstractDocumentBackend]

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @model_validator(mode="after")
    def set_optional_field_default(self) -> "FormatOption":
        if self.pipeline_options is None:
            self.pipeline_options = self.pipeline_cls.get_default_options()
        return self


class WordFormatOption(FormatOption):
    pipeline_cls: Type = SimpleModelPipeline
    backend: Type[AbstractDocumentBackend] = MsWordDocumentBackend


class PowerpointFormatOption(FormatOption):
    pipeline_cls: Type = SimpleModelPipeline
    backend: Type[AbstractDocumentBackend] = MsPowerpointDocumentBackend


class HTMLFormatOption(FormatOption):
    pipeline_cls: Type = SimpleModelPipeline
    backend: Type[AbstractDocumentBackend] = HTMLDocumentBackend


class PdfFormatOption(FormatOption):
    pipeline_cls: Type = StandardPdfModelPipeline
    backend: Type[AbstractDocumentBackend] = DoclingParseDocumentBackend


_format_to_default_options = {
    InputFormat.DOCX: FormatOption(
        pipeline_cls=SimpleModelPipeline, backend=MsWordDocumentBackend
    ),
    InputFormat.PPTX: FormatOption(
        pipeline_cls=SimpleModelPipeline, backend=MsPowerpointDocumentBackend
    ),
    InputFormat.HTML: FormatOption(
        pipeline_cls=SimpleModelPipeline, backend=HTMLDocumentBackend
    ),
    InputFormat.IMAGE: FormatOption(
        pipeline_cls=StandardPdfModelPipeline, backend=DoclingParseDocumentBackend
    ),
    InputFormat.PDF: FormatOption(
        pipeline_cls=StandardPdfModelPipeline, backend=DoclingParseDocumentBackend
    ),
}


class DocumentConverter:
    _default_download_filename = "file"

    def __init__(
        self,
        formats: Optional[List[InputFormat]] = None,
        format_options: Optional[Dict[InputFormat, FormatOption]] = None,
    ):
        self.formats = formats
        self.format_to_options = format_options

        if self.formats is None:
            if self.format_to_options is not None:
                self.formats = self.format_to_options.keys()
            else:
                self.formats = [e for e in InputFormat]  # all formats

        if self.format_to_options is None:
            self.format_to_options = _format_to_default_options

        for f in self.formats:
            if f not in self.format_to_options.keys():
                _log.info(f"Requested format {f} will use default options.")
                self.format_to_options[f] = _format_to_default_options[f]

        self.initialized_pipelines: Dict[
            Type[AbstractModelPipeline], AbstractModelPipeline
        ] = {}

    @deprecated("Use convert_batch instead.")
    def convert(self, input: DocumentConversionInput) -> Iterable[ConversionResult]:
        yield from self.convert_batch(input=input)

    def convert_batch(
        self, input: DocumentConversionInput, raise_on_error: bool = False
    ) -> Iterable[ConversionResult]:

        for input_batch in chunkify(
            input.docs(self.format_to_options),
            settings.perf.doc_batch_size,  # pass format_options
        ):
            _log.info(f"Going to convert document batch...")
            # parallel processing only within input_batch
            # with ThreadPoolExecutor(
            #    max_workers=settings.perf.doc_batch_concurrency
            # ) as pool:
            #   yield from pool.map(self.process_document, input_batch)

            # Note: PDF backends are not thread-safe, thread pool usage was disabled.
            for item in map(self.process_document, input_batch):
                if item is not None:
                    yield item

    def convert_single(
        self, source: Path | AnyHttpUrl | str, raise_on_error: bool = False
    ) -> ConversionResult:
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
            conv_res_iter = self.convert_batch(conv_inp)
            conv_res: ConversionResult = next(conv_res_iter)
        if conv_res.status not in {
            ConversionStatus.SUCCESS,
            ConversionStatus.PARTIAL_SUCCESS,
        }:
            raise RuntimeError(f"Conversion failed with status: {conv_res.status}")
        return conv_res

    def _get_pipeline(self, doc: InputDocument) -> Optional[AbstractModelPipeline]:
        fopt = self.format_to_options.get(doc.format)

        if fopt is None:
            raise RuntimeError(f"Could not get pipeline for document {doc.file}")
        else:
            pipeline_class = fopt.pipeline_cls
            pipeline_options = fopt.pipeline_options

        # TODO this will ignore if different options have been defined for the same pipeline class.
        if (
            pipeline_class not in self.initialized_pipelines
            or self.initialized_pipelines[pipeline_class].pipeline_options
            != pipeline_options
        ):
            self.initialized_pipelines[pipeline_class] = pipeline_class(
                pipeline_options=pipeline_options
            )
        return self.initialized_pipelines[pipeline_class]

    def process_document(self, in_doc: InputDocument) -> ConversionResult:
        if in_doc.format not in self.formats:
            return None
        else:
            start_doc_time = time.time()

            conv_res = self._execute_pipeline(in_doc)

            end_doc_time = time.time() - start_doc_time
            _log.info(f"Finished converting document in {end_doc_time:.2f} seconds.")

            return conv_res

    def _execute_pipeline(self, in_doc: InputDocument) -> Optional[ConversionResult]:
        if in_doc.valid:
            pipeline = self._get_pipeline(in_doc)
            if pipeline is None:  # Can't find a default pipeline. Should this raise?
                conv_res = ConversionResult(input=in_doc)
                conv_res.status = ConversionStatus.FAILURE
                return conv_res

            conv_res = pipeline.execute(in_doc)

        else:
            # invalid doc or not of desired format
            conv_res = ConversionResult(input=in_doc)
            conv_res.status = ConversionStatus.FAILURE
            # TODO add error log why it failed.

        return conv_res
