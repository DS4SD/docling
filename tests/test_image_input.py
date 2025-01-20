from io import BytesIO
from pathlib import Path

import pytest

from docling.datamodel.base_models import DocumentStream
from docling.document_converter import DocumentConverter

from .verify_utils import verify_conversion_result_v2

GENERATE = False


def get_doc_path():

    pdf_path = Path("./tests/data/2305.03393v1-pg9-img.png")
    return pdf_path


@pytest.fixture
def converter():

    converter = DocumentConverter()

    return converter


def test_convert_path(converter: DocumentConverter):

    doc_path = get_doc_path()
    print(f"converting {doc_path}")

    doc_result = converter.convert(doc_path)
    verify_conversion_result_v2(
        input_path=doc_path, doc_result=doc_result, generate=GENERATE
    )


def test_convert_stream(converter: DocumentConverter):

    doc_path = get_doc_path()
    print(f"converting {doc_path}")

    buf = BytesIO(doc_path.open("rb").read())
    stream = DocumentStream(name=doc_path.name, stream=buf)

    doc_result = converter.convert(stream)
    verify_conversion_result_v2(
        input_path=doc_path, doc_result=doc_result, generate=GENERATE
    )
