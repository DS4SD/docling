import sys
from pathlib import Path
from typing import List

from docling.backend.docling_parse_backend import DoclingParseDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import ConversionResult
from docling.datamodel.pipeline_options import (
    EasyOcrOptions,
    OcrMacOptions,
    OcrOptions,
    PdfPipelineOptions,
    RapidOcrOptions,
    TesseractCliOcrOptions,
    TesseractOcrOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption

from .verify_utils import verify_conversion_result_v1, verify_conversion_result_v2

GENERATE_V1 = False
GENERATE_V2 = False


def get_pdf_paths():
    # Define the directory you want to search
    directory = Path("./tests/data_scanned")

    # List all PDF files in the directory and its subdirectories
    pdf_files = sorted(directory.rglob("*.pdf"))
    return pdf_files


def get_converter(ocr_options: OcrOptions):
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options.do_cell_matching = True
    pipeline_options.ocr_options = ocr_options

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options,
                backend=DoclingParseDocumentBackend,
            )
        }
    )

    return converter


def test_e2e_conversions():
    pdf_paths = get_pdf_paths()

    engines: List[OcrOptions] = [
        EasyOcrOptions(),
        TesseractOcrOptions(),
        TesseractCliOcrOptions(),
        RapidOcrOptions(),
        EasyOcrOptions(force_full_page_ocr=True),
        TesseractOcrOptions(force_full_page_ocr=True),
        TesseractCliOcrOptions(force_full_page_ocr=True),
        RapidOcrOptions(force_full_page_ocr=True),
    ]

    # only works on mac
    if "darwin" == sys.platform:
        engines.append(OcrMacOptions())
        engines.append(OcrMacOptions(force_full_page_ocr=True))

    for ocr_options in engines:
        print(f"Converting with ocr_engine: {ocr_options.kind}")
        converter = get_converter(ocr_options=ocr_options)
        for pdf_path in pdf_paths:
            print(f"converting {pdf_path}")

            doc_result: ConversionResult = converter.convert(pdf_path)

            verify_conversion_result_v1(
                input_path=pdf_path,
                doc_result=doc_result,
                generate=GENERATE_V1,
                fuzzy=True,
            )

            verify_conversion_result_v2(
                input_path=pdf_path,
                doc_result=doc_result,
                generate=GENERATE_V2,
                fuzzy=True,
            )
