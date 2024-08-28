import glob
import json
from pathlib import Path, PosixPath
from typing import List

from docling_core.types import BaseText
from docling_core.types import Document as DsDocument
from pydantic import TypeAdapter
from pydantic.json import pydantic_encoder

from docling.backend.docling_parse_backend import DoclingParseDocumentBackend
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.base_models import ConversionStatus, Page, PipelineOptions
from docling.datamodel.document import ConversionResult
from docling.document_converter import DocumentConverter

GENERATE = False


def get_pdf_paths():

    # Define the directory you want to search
    directory = Path("./tests/data")

    # List all PDF files in the directory and its subdirectories
    pdf_files = sorted(directory.rglob("*.pdf"))
    return pdf_files


def get_converter():

    pipeline_options = PipelineOptions()
    pipeline_options.do_ocr = False
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options.do_cell_matching = True

    converter = DocumentConverter(
        pipeline_options=pipeline_options,
        pdf_backend=DoclingParseDocumentBackend,
    )

    return converter


def verify_cells(doc_pred_pages, doc_true_pages):

    assert len(doc_pred_pages) == len(
        doc_true_pages
    ), "pred- and true-doc do not have the same number of pages"

    for pid, page_true_item in enumerate(doc_true_pages):

        num_true_cells = len(page_true_item.cells)
        num_pred_cells = len(doc_pred_pages[pid].cells)

        assert (
            num_true_cells == num_pred_cells
        ), f"num_true_cells!=num_pred_cells {num_true_cells}!={num_pred_cells}"

        for cid, cell_true_item in enumerate(page_true_item.cells):

            cell_pred_item = doc_pred_pages[pid].cells[cid]

            true_text = cell_true_item.text
            pred_text = cell_pred_item.text

            assert true_text == pred_text, f"{true_text}!={pred_text}"

            true_bbox = cell_true_item.bbox.as_tuple()
            pred_bbox = cell_pred_item.bbox.as_tuple()
            assert (
                true_bbox == pred_bbox
            ), f"bbox is not the same: {true_bbox} != {pred_bbox}"

    return True


def verify_maintext(doc_pred, doc_true):

    assert len(doc_true.main_text) == len(
        doc_pred.main_text
    ), "document has different length of main-text than expected."

    for l, true_item in enumerate(doc_true.main_text):
        if isinstance(true_item, BaseText):
            pred_item = doc_pred.main_text[l]

            assert isinstance(
                pred_item, BaseText
            ), f"{pred_item} is not a BaseText element, but {true_item} is."
            assert true_item.text == pred_item.text

    return True


def verify_tables(doc_pred, doc_true):
    assert len(doc_true.tables) == len(
        doc_pred.tables
    ), "document has different count of tables than expected."

    for l, true_item in enumerate(doc_true.tables):
        pred_item = doc_pred.tables[l]

        assert (
            true_item.num_rows == pred_item.num_rows
        ), "table does not have the same #-rows"
        assert (
            true_item.num_cols == pred_item.num_cols
        ), "table does not have the same #-cols"

        for i, row in enumerate(true_item.data):
            for j, col in enumerate(true_item.data[i]):

                assert (
                    true_item.data[i][j].text == pred_item.data[i][j].text
                ), "table-cell does not have the same text"

    return True


def verify_output(doc_pred: DsDocument, doc_true: DsDocument):

    assert verify_maintext(doc_pred, doc_true), "verify_maintext(doc_pred, doc_true)"
    assert verify_tables(doc_pred, doc_true), "verify_tables(doc_pred, doc_true)"

    return True


def verify_md(doc_pred_md, doc_true_md):
    return doc_pred_md == doc_true_md


def test_e2e_conversions():
    PageList = TypeAdapter(List[Page])

    pdf_paths = get_pdf_paths()
    converter = get_converter()

    for path in pdf_paths:
        print(f"converting {path}")

        try:
            doc_result: ConversionResult = converter.convert_single(path)
        except:
            continue

        doc_pred_pages: PageList = doc_result.pages
        doc_pred: DsDocument = doc_result.output
        doc_pred_md = doc_result.render_as_markdown()

        pages_path = path.with_suffix(".pages.json")
        json_path = path.with_suffix(".json")
        md_path = path.with_suffix(".md")

        if GENERATE:  # only used when re-generating truth
            with open(pages_path, "w") as fw:
                fw.write(json.dumps(doc_pred_pages, default=pydantic_encoder))

            with open(json_path, "w") as fw:
                fw.write(json.dumps(doc_pred, default=pydantic_encoder))

            with open(md_path, "w") as fw:
                fw.write(doc_pred_md)
        else:  # default branch in test
            with open(pages_path, "r") as fr:
                doc_true_pages = PageList.validate_python(json.load(fr))

            with open(json_path, "r") as fr:
                doc_true = DsDocument.model_validate(json.load(fr))

            with open(md_path, "r") as fr:
                doc_true_md = "".join(fr.readlines())

            assert verify_cells(
                doc_pred_pages, doc_true_pages
            ), f"Mismatch in PDF cell prediction for {path}"

            assert verify_output(
                doc_pred, doc_true
            ), f"Mismatch in JSON prediction for {path}"

            assert verify_md(
                doc_pred_md, doc_true_md
            ), f"Mismatch in Markdown prediction for {path}"
