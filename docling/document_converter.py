import logging
import sys
import time
from functools import partial
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Type, Union

from pydantic import BaseModel, ConfigDict, model_validator, validate_call

from docling.backend.abstract_backend import AbstractDocumentBackend
from docling.backend.asciidoc_backend import AsciiDocBackend
from docling.backend.docling_parse_backend import DoclingParseDocumentBackend
from docling.backend.html_backend import HTMLDocumentBackend
from docling.backend.md_backend import MarkdownDocumentBackend
from docling.backend.msexcel_backend import MsExcelDocumentBackend
from docling.backend.mspowerpoint_backend import MsPowerpointDocumentBackend
from docling.backend.msword_backend import MsWordDocumentBackend
from docling.datamodel.base_models import (
    ConversionStatus,
    DoclingComponentType,
    DocumentStream,
    ErrorItem,
    InputFormat,
)
from docling.datamodel.document import (
    ConversionResult,
    InputDocument,
    _DocumentConversionInput,
)
from docling.datamodel.pipeline_options import PipelineOptions
from docling.datamodel.settings import DocumentLimits, settings
from docling.exceptions import ConversionError
from docling.pipeline.base_pipeline import BasePipeline
from docling.pipeline.simple_pipeline import SimplePipeline
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline
from docling.utils.utils import chunkify

_log = logging.getLogger(__name__)


class FormatOption(BaseModel):
    pipeline_cls: Type[BasePipeline]
    pipeline_options: Optional[PipelineOptions] = None
    backend: Type[AbstractDocumentBackend]

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @model_validator(mode="after")
    def set_optional_field_default(self) -> "FormatOption":
        if self.pipeline_options is None:
            self.pipeline_options = self.pipeline_cls.get_default_options()
        return self


class ExcelFormatOption(FormatOption):
    pipeline_cls: Type = SimplePipeline
    backend: Type[AbstractDocumentBackend] = MsExcelDocumentBackend


class WordFormatOption(FormatOption):
    pipeline_cls: Type = SimplePipeline
    backend: Type[AbstractDocumentBackend] = MsWordDocumentBackend


class PowerpointFormatOption(FormatOption):
    pipeline_cls: Type = SimplePipeline
    backend: Type[AbstractDocumentBackend] = MsPowerpointDocumentBackend


class MarkdownFormatOption(FormatOption):
    pipeline_cls: Type = SimplePipeline
    backend: Type[AbstractDocumentBackend] = MarkdownDocumentBackend


class AsciiDocFormatOption(FormatOption):
    pipeline_cls: Type = SimplePipeline
    backend: Type[AbstractDocumentBackend] = AsciiDocBackend


class HTMLFormatOption(FormatOption):
    pipeline_cls: Type = SimplePipeline
    backend: Type[AbstractDocumentBackend] = HTMLDocumentBackend


class PdfFormatOption(FormatOption):
    pipeline_cls: Type = StandardPdfPipeline
    backend: Type[AbstractDocumentBackend] = DoclingParseDocumentBackend


class ImageFormatOption(FormatOption):
    pipeline_cls: Type = StandardPdfPipeline
    backend: Type[AbstractDocumentBackend] = DoclingParseDocumentBackend


def _get_default_option(format: InputFormat) -> FormatOption:
    format_to_default_options = {
        InputFormat.XLSX: FormatOption(
            pipeline_cls=SimplePipeline, backend=MsExcelDocumentBackend
        ),
        InputFormat.DOCX: FormatOption(
            pipeline_cls=SimplePipeline, backend=MsWordDocumentBackend
        ),
        InputFormat.PPTX: FormatOption(
            pipeline_cls=SimplePipeline, backend=MsPowerpointDocumentBackend
        ),
        InputFormat.MD: FormatOption(
            pipeline_cls=SimplePipeline, backend=MarkdownDocumentBackend
        ),
        InputFormat.ASCIIDOC: FormatOption(
            pipeline_cls=SimplePipeline, backend=AsciiDocBackend
        ),
        InputFormat.HTML: FormatOption(
            pipeline_cls=SimplePipeline, backend=HTMLDocumentBackend
        ),
        InputFormat.IMAGE: FormatOption(
            pipeline_cls=StandardPdfPipeline, backend=DoclingParseDocumentBackend
        ),
        InputFormat.PDF: FormatOption(
            pipeline_cls=StandardPdfPipeline, backend=DoclingParseDocumentBackend
        ),
    }
    if (options := format_to_default_options.get(format)) is not None:
        return options
    else:
        raise RuntimeError(f"No default options configured for {format}")


class DocumentConverter:
    _default_download_filename = "file"

    def __init__(
        self,
        allowed_formats: Optional[List[InputFormat]] = None,
        format_options: Optional[Dict[InputFormat, FormatOption]] = None,
    ):
        self.allowed_formats = (
            allowed_formats if allowed_formats is not None else [e for e in InputFormat]
        )
        self.format_to_options = {
            format: (
                _get_default_option(format=format)
                if (custom_option := (format_options or {}).get(format)) is None
                else custom_option
            )
            for format in self.allowed_formats
        }
        self.initialized_pipelines: Dict[Type[BasePipeline], BasePipeline] = {}

    def initialize_pipeline(self, format: InputFormat):
        """Initialize the conversion pipeline for the selected format."""
        pipeline = self._get_pipeline(doc_format=format)
        if pipeline is None:
            raise ConversionError(
                f"No pipeline could be initialized for format {format}"
            )

    @validate_call(config=ConfigDict(strict=True))
    def convert(
        self,
        source: Union[Path, str, DocumentStream],  # TODO review naming
        raises_on_error: bool = True,
        max_num_pages: int = sys.maxsize,
        max_file_size: int = sys.maxsize,
    ) -> ConversionResult:

        all_res = self.convert_all(
            source=[source],
            raises_on_error=raises_on_error,
            max_num_pages=max_num_pages,
            max_file_size=max_file_size,
        )
        return next(all_res)

    @validate_call(config=ConfigDict(strict=True))
    def convert_all(
        self,
        source: Iterable[Union[Path, str, DocumentStream]],  # TODO review naming
        raises_on_error: bool = True,  # True: raises on first conversion error; False: does not raise on conv error
        max_num_pages: int = sys.maxsize,
        max_file_size: int = sys.maxsize,
    ) -> Iterator[ConversionResult]:
        limits = DocumentLimits(
            max_num_pages=max_num_pages,
            max_file_size=max_file_size,
        )
        conv_input = _DocumentConversionInput(
            path_or_stream_iterator=source,
            limits=limits,
        )
        conv_res_iter = self._convert(conv_input, raises_on_error=raises_on_error)

        had_result = False
        for conv_res in conv_res_iter:
            had_result = True
            if raises_on_error and conv_res.status not in {
                ConversionStatus.SUCCESS,
                ConversionStatus.PARTIAL_SUCCESS,
            }:
                raise ConversionError(
                    f"Conversion failed for: {conv_res.input.file} with status: {conv_res.status}"
                )
            else:
                yield conv_res

        if not had_result and raises_on_error:
            raise ConversionError(
                f"Conversion failed because the provided file has no recognizable format or it wasn't in the list of allowed formats."
            )

    def _convert(
        self, conv_input: _DocumentConversionInput, raises_on_error: bool
    ) -> Iterator[ConversionResult]:
        start_time = time.monotonic()

        for input_batch in chunkify(
            conv_input.docs(self.format_to_options),
            settings.perf.doc_batch_size,  # pass format_options
        ):
            _log.info(f"Going to convert document batch...")

            # parallel processing only within input_batch
            # with ThreadPoolExecutor(
            #    max_workers=settings.perf.doc_batch_concurrency
            # ) as pool:
            #   yield from pool.map(self.process_document, input_batch)
            # Note: PDF backends are not thread-safe, thread pool usage was disabled.

            for item in map(
                partial(self._process_document, raises_on_error=raises_on_error),
                input_batch,
            ):
                elapsed = time.monotonic() - start_time
                start_time = time.monotonic()
                _log.info(
                    f"Finished converting document {item.input.file.name} in {elapsed:.2f} sec."
                )
                yield item

    def _get_pipeline(self, doc_format: InputFormat) -> Optional[BasePipeline]:
        fopt = self.format_to_options.get(doc_format)

        if fopt is None:
            return None
        else:
            pipeline_class = fopt.pipeline_cls
            pipeline_options = fopt.pipeline_options

        if pipeline_options is None:
            return None
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

    def _process_document(
        self, in_doc: InputDocument, raises_on_error: bool
    ) -> ConversionResult:

        valid = (
            self.allowed_formats is not None and in_doc.format in self.allowed_formats
        )
        if valid:
            conv_res = self._execute_pipeline(in_doc, raises_on_error=raises_on_error)
        else:
            error_message = f"File format not allowed: {in_doc.file}"
            if raises_on_error:
                raise ConversionError(error_message)
            else:
                error_item = ErrorItem(
                    component_type=DoclingComponentType.USER_INPUT,
                    module_name="",
                    error_message=error_message,
                )
                conv_res = ConversionResult(
                    input=in_doc, status=ConversionStatus.SKIPPED, errors=[error_item]
                )

        return conv_res

    def _execute_pipeline(
        self, in_doc: InputDocument, raises_on_error: bool
    ) -> ConversionResult:
        if in_doc.valid:
            pipeline = self._get_pipeline(in_doc.format)
            if pipeline is not None:
                conv_res = pipeline.execute(in_doc, raises_on_error=raises_on_error)
            else:
                if raises_on_error:
                    raise ConversionError(
                        f"No pipeline could be initialized for {in_doc.file}."
                    )
                else:
                    conv_res = ConversionResult(
                        input=in_doc,
                        status=ConversionStatus.FAILURE,
                    )
        else:
            if raises_on_error:
                raise ConversionError(f"Input document {in_doc.file} is not valid.")

            else:
                # invalid doc or not of desired format
                conv_res = ConversionResult(
                    input=in_doc,
                    status=ConversionStatus.FAILURE,
                )
                # TODO add error log why it failed.

        return conv_res
