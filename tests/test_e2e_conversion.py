from pathlib import Path

from docling.backend.docling_parse_backend import DoclingParseDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import ConversionResult
from docling.datamodel.pipeline_options import PdfPipelineOptions, PipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

from .verify_utils import verify_conversion_result

GENERATE = False


def get_pdf_paths():

    # Define the directory you want to search
    directory = Path("./tests/data")

    # List all PDF files in the directory and its subdirectories
    pdf_files = sorted(directory.rglob("*.pdf"))
    return pdf_files


def get_converter():

    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = False
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options.do_cell_matching = True

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options, backend=DoclingParseDocumentBackend
            )
        }
    )

    return converter


def test_e2e_conversions():

    pdf_paths = get_pdf_paths()
    converter = get_converter()

    for pdf_path in pdf_paths:
        print(f"converting {pdf_path}")

        doc_result: ConversionResult = converter.convert_single(pdf_path)

        verify_conversion_result(
            input_path=pdf_path, doc_result=doc_result, generate=GENERATE
        )
