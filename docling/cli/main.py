import importlib
import json
import logging
import re
import time
import warnings
from enum import Enum
from pathlib import Path
from typing import Annotated, Dict, Iterable, List, Optional, Type

import typer
from docling_core.utils.file import resolve_file_source

from docling.backend.docling_parse_backend import DoclingParseDocumentBackend
from docling.backend.docling_parse_v2_backend import DoclingParseV2DocumentBackend
from docling.backend.pdf_backend import PdfDocumentBackend
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.base_models import (
    ConversionStatus,
    FormatToExtensions,
    InputFormat,
    OutputFormat,
)
from docling.datamodel.document import ConversionResult
from docling.datamodel.pipeline_options import (
    EasyOcrOptions,
    OcrMacOptions,
    OcrOptions,
    PdfPipelineOptions,
    TableFormerMode,
    TesseractCliOcrOptions,
    TesseractOcrOptions,
)
from docling.document_converter import DocumentConverter, FormatOption, PdfFormatOption

warnings.filterwarnings(action="ignore", category=UserWarning, module="pydantic|torch")
warnings.filterwarnings(action="ignore", category=FutureWarning, module="easyocr")

_log = logging.getLogger(__name__)
from rich.console import Console

err_console = Console(stderr=True)


app = typer.Typer(
    name="Docling",
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_enable=False,
)


def version_callback(value: bool):
    if value:
        docling_version = importlib.metadata.version("docling")
        docling_core_version = importlib.metadata.version("docling-core")
        docling_ibm_models_version = importlib.metadata.version("docling-ibm-models")
        docling_parse_version = importlib.metadata.version("docling-parse")
        print(f"Docling version: {docling_version}")
        print(f"Docling Core version: {docling_core_version}")
        print(f"Docling IBM Models version: {docling_ibm_models_version}")
        print(f"Docling Parse version: {docling_parse_version}")
        raise typer.Exit()


# Define an enum for the backend options
class PdfBackend(str, Enum):
    PYPDFIUM2 = "pypdfium2"
    DLPARSE_V1 = "dlparse_v1"
    DLPARSE_V2 = "dlparse_v2"


# Define an enum for the ocr engines
class OcrEngine(str, Enum):
    EASYOCR = "easyocr"
    TESSERACT_CLI = "tesseract_cli"
    TESSERACT = "tesseract"
    OCRMAC = "ocrmac"


def export_documents(
    conv_results: Iterable[ConversionResult],
    output_dir: Path,
    export_json: bool,
    export_md: bool,
    export_txt: bool,
    export_doctags: bool,
):

    success_count = 0
    failure_count = 0

    for conv_res in conv_results:
        if conv_res.status == ConversionStatus.SUCCESS:
            success_count += 1
            doc_filename = conv_res.input.file.stem

            # Export Deep Search document JSON format:
            if export_json:
                fname = output_dir / f"{doc_filename}.json"
                with fname.open("w", encoding="utf8") as fp:
                    _log.info(f"writing JSON output to {fname}")
                    fp.write(json.dumps(conv_res.document.export_to_dict()))

            # Export Text format:
            if export_txt:
                fname = output_dir / f"{doc_filename}.txt"
                with fname.open("w", encoding="utf8") as fp:
                    _log.info(f"writing Text output to {fname}")
                    fp.write(conv_res.document.export_to_markdown(strict_text=True))

            # Export Markdown format:
            if export_md:
                fname = output_dir / f"{doc_filename}.md"
                with fname.open("w", encoding="utf8") as fp:
                    _log.info(f"writing Markdown output to {fname}")
                    fp.write(conv_res.document.export_to_markdown())

            # Export Document Tags format:
            if export_doctags:
                fname = output_dir / f"{doc_filename}.doctags"
                with fname.open("w", encoding="utf8") as fp:
                    _log.info(f"writing Doc Tags output to {fname}")
                    fp.write(conv_res.document.export_to_document_tokens())

        else:
            _log.warning(f"Document {conv_res.input.file} failed to convert.")
            failure_count += 1

    _log.info(
        f"Processed {success_count + failure_count} docs, of which {failure_count} failed"
    )


def _split_list(raw: Optional[str]) -> Optional[List[str]]:
    if raw is None:
        return None
    return re.split(r"[;,]", raw)


@app.command(no_args_is_help=True)
def convert(
    input_sources: Annotated[
        List[str],
        typer.Argument(
            ...,
            metavar="source",
            help="PDF files to convert. Can be local file / directory paths or URL.",
        ),
    ],
    from_formats: List[InputFormat] = typer.Option(
        None,
        "--from",
        help="Specify input formats to convert from. Defaults to all formats.",
    ),
    to_formats: List[OutputFormat] = typer.Option(
        None, "--to", help="Specify output formats. Defaults to Markdown."
    ),
    ocr: Annotated[
        bool,
        typer.Option(
            ..., help="If enabled, the bitmap content will be processed using OCR."
        ),
    ] = True,
    force_ocr: Annotated[
        bool,
        typer.Option(
            ...,
            help="Replace any existing text with OCR generated text over the full content.",
        ),
    ] = False,
    ocr_engine: Annotated[
        OcrEngine, typer.Option(..., help="The OCR engine to use.")
    ] = OcrEngine.EASYOCR,
    ocr_lang: Annotated[
        Optional[str],
        typer.Option(
            ...,
            help="Provide a comma-separated list of languages used by the OCR engine. Note that each OCR engine has different values for the language names.",
        ),
    ] = None,
    pdf_backend: Annotated[
        PdfBackend, typer.Option(..., help="The PDF backend to use.")
    ] = PdfBackend.DLPARSE_V1,
    table_mode: Annotated[
        TableFormerMode,
        typer.Option(..., help="The mode to use in the table structure model."),
    ] = TableFormerMode.FAST,
    artifacts_path: Annotated[
        Optional[Path],
        typer.Option(..., help="If provided, the location of the model artifacts."),
    ] = None,
    abort_on_error: Annotated[
        bool,
        typer.Option(
            ...,
            "--abort-on-error/--no-abort-on-error",
            help="If enabled, the bitmap content will be processed using OCR.",
        ),
    ] = False,
    output: Annotated[
        Path, typer.Option(..., help="Output directory where results are saved.")
    ] = Path("."),
    verbose: Annotated[
        int,
        typer.Option(
            "--verbose",
            "-v",
            count=True,
            help="Set the verbosity level. -v for info logging, -vv for debug logging.",
        ),
    ] = 0,
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version",
            callback=version_callback,
            is_eager=True,
            help="Show version information.",
        ),
    ] = None,
):
    if verbose == 0:
        logging.basicConfig(level=logging.WARNING)
    elif verbose == 1:
        logging.basicConfig(level=logging.INFO)
    elif verbose == 2:
        logging.basicConfig(level=logging.DEBUG)

    if from_formats is None:
        from_formats = [e for e in InputFormat]

    input_doc_paths: List[Path] = []
    for src in input_sources:
        source = resolve_file_source(source=src)
        if not source.exists():
            err_console.print(
                f"[red]Error: The input file {source} does not exist.[/red]"
            )
            raise typer.Abort()
        elif source.is_dir():
            for fmt in from_formats:
                for ext in FormatToExtensions[fmt]:
                    input_doc_paths.extend(list(source.glob(f"**/*.{ext}")))
                    input_doc_paths.extend(list(source.glob(f"**/*.{ext.upper()}")))
        else:
            input_doc_paths.append(source)

    if to_formats is None:
        to_formats = [OutputFormat.MARKDOWN]

    export_json = OutputFormat.JSON in to_formats
    export_md = OutputFormat.MARKDOWN in to_formats
    export_txt = OutputFormat.TEXT in to_formats
    export_doctags = OutputFormat.DOCTAGS in to_formats

    if ocr_engine == OcrEngine.EASYOCR:
        ocr_options: OcrOptions = EasyOcrOptions(force_full_page_ocr=force_ocr)
    elif ocr_engine == OcrEngine.TESSERACT_CLI:
        ocr_options = TesseractCliOcrOptions(force_full_page_ocr=force_ocr)
    elif ocr_engine == OcrEngine.TESSERACT:
        ocr_options = TesseractOcrOptions(force_full_page_ocr=force_ocr)
    elif ocr_engine == OcrEngine.OCRMAC:
        ocr_options = OcrMacOptions(force_full_page_ocr=force_ocr)
    else:
        raise RuntimeError(f"Unexpected OCR engine type {ocr_engine}")

    ocr_lang_list = _split_list(ocr_lang)
    if ocr_lang_list is not None:
        ocr_options.lang = ocr_lang_list

    pipeline_options = PdfPipelineOptions(
        do_ocr=ocr,
        ocr_options=ocr_options,
        do_table_structure=True,
    )
    pipeline_options.table_structure_options.do_cell_matching = True  # do_cell_matching
    pipeline_options.table_structure_options.mode = table_mode

    if artifacts_path is not None:
        pipeline_options.artifacts_path = artifacts_path

    if pdf_backend == PdfBackend.DLPARSE_V1:
        backend: Type[PdfDocumentBackend] = DoclingParseDocumentBackend
    elif pdf_backend == PdfBackend.DLPARSE_V2:
        backend = DoclingParseV2DocumentBackend
    elif pdf_backend == PdfBackend.PYPDFIUM2:
        backend = PyPdfiumDocumentBackend
    else:
        raise RuntimeError(f"Unexpected PDF backend type {pdf_backend}")

    format_options: Dict[InputFormat, FormatOption] = {
        InputFormat.PDF: PdfFormatOption(
            pipeline_options=pipeline_options,
            backend=backend,  # pdf_backend
        )
    }
    doc_converter = DocumentConverter(
        allowed_formats=from_formats,
        format_options=format_options,
    )

    start_time = time.time()

    conv_results = doc_converter.convert_all(
        input_doc_paths, raises_on_error=abort_on_error
    )

    output.mkdir(parents=True, exist_ok=True)
    export_documents(
        conv_results,
        output_dir=output,
        export_json=export_json,
        export_md=export_md,
        export_txt=export_txt,
        export_doctags=export_doctags,
    )

    end_time = time.time() - start_time

    _log.info(f"All documents were converted in {end_time:.2f} seconds.")


click_app = typer.main.get_command(app)

if __name__ == "__main__":
    app()
