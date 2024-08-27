import json
import logging
import time
from pathlib import Path
from typing import Iterable

from docling.backend.docling_parse_backend import DoclingParseDocumentBackend
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.base_models import ConversionStatus, PipelineOptions
from docling.datamodel.document import ConversionResult, DocumentConversionInput
from docling.document_converter import DocumentConverter

_log = logging.getLogger(__name__)


def export_documents(
    conv_results: Iterable[ConversionResult],
    output_dir: Path,
):
    output_dir.mkdir(parents=True, exist_ok=True)

    success_count = 0
    failure_count = 0

    for conv_res in conv_results:
        if conv_res.status == ConversionStatus.SUCCESS:
            success_count += 1
            doc_filename = conv_res.input.file.stem

            # Export Deep Search document JSON format:
            with (output_dir / f"{doc_filename}.json").open("w") as fp:
                fp.write(json.dumps(conv_res.render_as_dict()))

            # Export Markdown format:
            with (output_dir / f"{doc_filename}.md").open("w") as fp:
                fp.write(conv_res.render_as_markdown())
        else:
            _log.info(f"Document {conv_res.input.file} failed to convert.")
            failure_count += 1

    _log.info(
        f"Processed {success_count + failure_count} docs, of which {failure_count} failed"
    )


def main():
    logging.basicConfig(level=logging.INFO)

    input_doc_paths = [
        Path("./test/data/2206.01062.pdf"),
        Path("./test/data/2203.01017v2.pdf"),
        Path("./test/data/2305.03393v1.pdf"),
    ]

    ###########################################################################

    # The following sections contain a combination of PipelineOptions
    # and PDF Backends for various configurations.
    # Uncomment one section at the time to see the differences in the output.

    # PyPdfium without OCR
    # --------------------
    # pipeline_options = PipelineOptions()
    # pipeline_options.do_ocr=False
    # pipeline_options.do_table_structure=True
    # pipeline_options.table_structure_options.do_cell_matching = False

    # doc_converter = DocumentConverter(
    #     pipeline_options=pipeline_options,
    #     pdf_backend=PyPdfiumDocumentBackend,
    # )

    # PyPdfium with OCR
    # -----------------
    # pipeline_options = PipelineOptions()
    # pipeline_options.do_ocr=False
    # pipeline_options.do_table_structure=True
    # pipeline_options.table_structure_options.do_cell_matching = True

    # doc_converter = DocumentConverter(
    #     pipeline_options=pipeline_options,
    #     pdf_backend=PyPdfiumDocumentBackend,
    # )

    # Docling Parse without OCR
    # -------------------------
    pipeline_options = PipelineOptions()
    pipeline_options.do_ocr = False
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options.do_cell_matching = True

    doc_converter = DocumentConverter(
        pipeline_options=pipeline_options,
        pdf_backend=DoclingParseDocumentBackend,
    )

    # Docling Parse with OCR
    # ----------------------
    # pipeline_options = PipelineOptions()
    # pipeline_options.do_ocr=True
    # pipeline_options.do_table_structure=True
    # pipeline_options.table_structure_options.do_cell_matching = True

    # doc_converter = DocumentConverter(
    #     pipeline_options=pipeline_options,
    #     pdf_backend=DoclingParseDocumentBackend,
    # )

    ###########################################################################

    # Define input files
    input = DocumentConversionInput.from_paths(input_doc_paths)

    start_time = time.time()

    conv_results = doc_converter.convert(input)
    export_documents(conv_results, output_dir=Path("./scratch"))

    end_time = time.time() - start_time

    _log.info(f"All documents were converted in {end_time:.2f} seconds.")


if __name__ == "__main__":
    main()
