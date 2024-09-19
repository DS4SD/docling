from io import BytesIO
from pathlib import Path

import pytest

from docling.backend.docling_parse_backend import DoclingParseDocumentBackend
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.base_models import DocumentStream
from docling.datamodel.document import ConversionResult, DocumentConversionInput
from docling.datamodel.pipeline_options import PipelineOptions
from docling.document_converter import DocumentConverter

from .verify_utils import verify_conversion_result


def get_pdf_path():

    pdf_path = Path("./tests/data/2305.03393v1-pg9.pdf")
    return pdf_path


@pytest.fixture
def converter():

    pipeline_options = PipelineOptions()
    pipeline_options.do_ocr = False
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options.do_cell_matching = True

    converter = DocumentConverter(
        pipeline_options=pipeline_options,
        pdf_backend=DoclingParseDocumentBackend,
    )

    return converter


def test_convert_single(converter: DocumentConverter):

    pdf_path = get_pdf_path()
    print(f"converting {pdf_path}")

    doc_result: ConversionResult = converter.convert_single(pdf_path)
    verify_conversion_result(input_path=pdf_path, doc_result=doc_result)


def test_batch_path(converter: DocumentConverter):

    pdf_path = get_pdf_path()
    print(f"converting {pdf_path}")

    conv_input = DocumentConversionInput.from_paths([pdf_path])

    results = converter.convert(conv_input)
    for doc_result in results:
        verify_conversion_result(input_path=pdf_path, doc_result=doc_result)


def test_batch_bytes(converter: DocumentConverter):

    pdf_path = get_pdf_path()
    print(f"converting {pdf_path}")

    buf = BytesIO(pdf_path.open("rb").read())
    docs = [DocumentStream(filename=pdf_path.name, stream=buf)]
    conv_input = DocumentConversionInput.from_streams(docs)

    results = converter.convert(conv_input)
    for doc_result in results:
        verify_conversion_result(input_path=pdf_path, doc_result=doc_result)
