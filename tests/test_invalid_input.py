from io import BytesIO
from pathlib import Path

import pytest

from docling.backend.docling_parse_backend import DoclingParseDocumentBackend
from docling.datamodel.base_models import ConversionStatus, DocumentStream, InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

from .verify_utils import verify_conversion_result_v1, verify_conversion_result_v2

GENERATE = False


def get_pdf_path():

    pdf_path = Path("./tests/data/2305.03393v1-pg9.pdf")
    return pdf_path


@pytest.fixture
def converter():
    converter = DocumentConverter()

    return converter


def test_convert_invalid_doc(converter: DocumentConverter):

    # Test with unrecognizable file format (xyz)
    result = converter.convert(
        DocumentStream(name="input.xyz", stream=BytesIO(b"xyz")), raises_on_error=False
    )
    assert result is None  # No result comes back at all, since this file is skipped.

    with pytest.raises(RuntimeError):
        result = converter.convert(
            DocumentStream(name="input.xyz", stream=BytesIO(b"xyz")),
            raises_on_error=True,
        )

    # Test with too small filesize limit
    result = converter.convert(get_pdf_path(), max_file_size=1, raises_on_error=False)
    assert result is not None
    assert result.status == ConversionStatus.FAILURE

    with pytest.raises(RuntimeError):
        result = converter.convert(
            get_pdf_path(), max_file_size=1, raises_on_error=True
        )