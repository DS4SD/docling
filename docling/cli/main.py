import importlib
import json
import logging
import time
import warnings
from enum import Enum
from pathlib import Path
from typing import Annotated, Iterable, List, Optional

import typer
from pydantic import AnyUrl

from docling.backend.docling_parse_backend import DoclingParseDocumentBackend
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.base_models import ConversionStatus, PipelineOptions
from docling.datamodel.document import ConversionResult, DocumentConversionInput
from docling.document_converter import DocumentConverter

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
class Backend(str, Enum):
    PYPDFIUM2 = "pypdfium2"
    DOCLING = "docling"


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
                with fname.open("w") as fp:
                    _log.info(f"writing JSON output to {fname}")
                    fp.write(json.dumps(conv_res.render_as_dict()))

            # Export Text format:
            if export_txt:
                fname = output_dir / f"{doc_filename}.txt"
                with fname.open("w") as fp:
                    _log.info(f"writing Text output to {fname}")
                    fp.write(conv_res.render_as_text())

            # Export Markdown format:
            if export_md:
                fname = output_dir / f"{doc_filename}.md"
                with fname.open("w") as fp:
                    _log.info(f"writing Markdown output to {fname}")
                    fp.write(conv_res.render_as_markdown())

            # Export Document Tags format:
            if export_doctags:
                fname = output_dir / f"{doc_filename}.doctags"
                with fname.open("w") as fp:
                    _log.info(f"writing Doc Tags output to {fname}")
                    fp.write(conv_res.render_as_doctags())

        else:
            _log.warning(f"Document {conv_res.input.file} failed to convert.")
            failure_count += 1

    _log.info(
        f"Processed {success_count + failure_count} docs, of which {failure_count} failed"
    )


@app.command(no_args_is_help=True)
def convert(
    input_sources: Annotated[
        List[Path],
        typer.Argument(
            ...,
            metavar="source",
            help="PDF files to convert. Directories are also accepted.",
        ),
    ],
    export_json: Annotated[
        bool,
        typer.Option(
            ..., "--json/--no-json", help="If enabled the document is exported as JSON."
        ),
    ] = False,
    export_md: Annotated[
        bool,
        typer.Option(
            ..., "--md/--no-md", help="If enabled the document is exported as Markdown."
        ),
    ] = True,
    export_txt: Annotated[
        bool,
        typer.Option(
            ..., "--txt/--no-txt", help="If enabled the document is exported as Text."
        ),
    ] = False,
    export_doctags: Annotated[
        bool,
        typer.Option(
            ...,
            "--doctags/--no-doctags",
            help="If enabled the document is exported as Doc Tags.",
        ),
    ] = False,
    ocr: Annotated[
        bool,
        typer.Option(
            ..., help="If enabled, the bitmap content will be processed using OCR."
        ),
    ] = True,
    backend: Annotated[
        Backend, typer.Option(..., help="The PDF backend to use.")
    ] = Backend.DOCLING,
    output: Annotated[
        Path, typer.Option(..., help="Output directory where results are saved.")
    ] = Path("."),
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
    logging.basicConfig(level=logging.INFO)

    input_doc_paths: List[Path] = []
    for source in input_sources:
        if not source.exists():
            err_console.print(
                f"[red]Error: The input file {source} does not exist.[/red]"
            )
            raise typer.Abort()
        elif source.is_dir():
            input_doc_paths.extend(list(source.glob("**/*.pdf")))
            input_doc_paths.extend(list(source.glob("**/*.PDF")))
        else:
            input_doc_paths.append(source)

    ###########################################################################

    # The following sections contain a combination of PipelineOptions
    # and PDF Backends for various configurations.
    # Uncomment one section at the time to see the differences in the output.

    doc_converter = None
    if backend == Backend.PYPDFIUM2 and not ocr:  # PyPdfium without OCR
        pipeline_options = PipelineOptions()
        pipeline_options.do_ocr = False
        pipeline_options.do_table_structure = True
        pipeline_options.table_structure_options.do_cell_matching = False

        doc_converter = DocumentConverter(
            pipeline_options=pipeline_options,
            pdf_backend=PyPdfiumDocumentBackend,
        )

    elif backend == Backend.PYPDFIUM2.value and ocr:  # PyPdfium with OCR
        pipeline_options = PipelineOptions()
        pipeline_options.do_ocr = False
        pipeline_options.do_table_structure = True
        pipeline_options.table_structure_options.do_cell_matching = True

        doc_converter = DocumentConverter(
            pipeline_options=pipeline_options,
            pdf_backend=PyPdfiumDocumentBackend,
        )

    elif backend == Backend.DOCLING.value and not ocr:  # Docling Parse without OCR
        pipeline_options = PipelineOptions()
        pipeline_options.do_ocr = False
        pipeline_options.do_table_structure = True
        pipeline_options.table_structure_options.do_cell_matching = True

        doc_converter = DocumentConverter(
            pipeline_options=pipeline_options,
            pdf_backend=DoclingParseDocumentBackend,
        )

    elif backend == Backend.DOCLING.value and ocr:  # Docling Parse with OCR
        pipeline_options = PipelineOptions()
        pipeline_options.do_ocr = True
        pipeline_options.do_table_structure = True
        pipeline_options.table_structure_options.do_cell_matching = True

        doc_converter = DocumentConverter(
            pipeline_options=pipeline_options,
            pdf_backend=DoclingParseDocumentBackend,
        )

    ###########################################################################

    # Define input files
    input = DocumentConversionInput.from_paths(input_doc_paths)

    start_time = time.time()

    conv_results = doc_converter.convert(input)

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


if __name__ == "__main__":
    app()
