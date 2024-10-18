from pathlib import Path

import pytest

from docling.backend.docling_parse_backend import DoclingParseDocumentBackend
from docling.datamodel.base_models import ConversionStatus, InputFormat
from docling.datamodel.document import ConversionResult
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.document_converter import DocumentConverter, PdfFormatOption


@pytest.fixture
def test_doc_path():
    return Path("./tests/data/2206.01062.pdf")


def get_converters_with_table_options():
    for cell_matching in [True, False]:
        for mode in [TableFormerMode.FAST, TableFormerMode.ACCURATE]:
            pipeline_options = PdfPipelineOptions()
            pipeline_options.do_ocr = False
            pipeline_options.do_table_structure = True
            pipeline_options.table_structure_options.do_cell_matching = cell_matching
            pipeline_options.table_structure_options.mode = mode

            converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(
                        pipeline_options=pipeline_options,
                        backend=DoclingParseDocumentBackend,
                    )
                }
            )

            yield converter


def test_e2e_conversions(test_doc_path):
    for converter in get_converters_with_table_options():
        print(f"converting {test_doc_path}")

        doc_result: ConversionResult = converter.convert(test_doc_path)

        assert doc_result.status == ConversionStatus.SUCCESS


def test_ocr_coverage_threshold(test_doc_path):
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.ocr_options.bitmap_area_threshold = 1.1

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options,
            )
        }
    )

    test_doc_path = Path("./tests/data_scanned/ocr_test.pdf")
    doc_result: ConversionResult = converter.convert(test_doc_path)

    # this should have generated no results, since we set a very high threshold
    assert len(doc_result.document.texts) == 0
