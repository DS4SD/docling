from pathlib import Path

import pytest

from docling.backend.docling_parse_backend import DoclingParseDocumentBackend
from docling.datamodel.base_models import ConversionStatus
from docling.datamodel.document import ConversionResult
from docling.datamodel.pipeline_options import PipelineOptions, TableFormerMode
from docling.document_converter import DocumentConverter

from .verify_utils import verify_conversion_result


@pytest.fixture
def test_doc_path():
    return Path("./tests/data/2206.01062.pdf")


def get_converters_with_table_options():
    for cell_matching in [True, False]:
        for mode in [TableFormerMode.FAST, TableFormerMode.ACCURATE]:
            pipeline_options = PipelineOptions()
            pipeline_options.do_ocr = False
            pipeline_options.do_table_structure = True
            pipeline_options.table_structure_options.do_cell_matching = cell_matching
            pipeline_options.table_structure_options.mode = mode

            converter = DocumentConverter(
                pipeline_options=pipeline_options,
                pdf_backend=DoclingParseDocumentBackend,
            )

            yield converter


def test_e2e_conversions(test_doc_path):
    for converter in get_converters_with_table_options():
        print(f"converting {test_doc_path}")

        doc_result: ConversionResult = converter.convert_single(test_doc_path)

        assert doc_result.status == ConversionStatus.SUCCESS
