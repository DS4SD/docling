import json
from pathlib import Path
from typing import List

from docling_core.types import BaseText
from docling_core.types import Document as DsDocument
from pydantic import TypeAdapter
from pydantic.json import pydantic_encoder

from docling.datamodel.base_models import ConversionStatus, Page
from docling.datamodel.document import ConversionResult


def verify_cells(doc_pred_pages: List[Page], doc_true_pages: List[Page]):

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


def verify_maintext(doc_pred: DsDocument, doc_true: DsDocument):
    assert doc_true.main_text is not None, "doc_true cannot be None"
    assert doc_pred.main_text is not None, "doc_true cannot be None"

    assert len(doc_true.main_text) == len(
        doc_pred.main_text
    ), f"document has different length of main-text than expected. {len(doc_true.main_text)}!={len(doc_pred.main_text)}"

    for l, true_item in enumerate(doc_true.main_text):
        pred_item = doc_pred.main_text[l]
        # Validate type
        assert (
            true_item.obj_type == pred_item.obj_type
        ), f"Item[{l}] type does not match. expected[{true_item.obj_type}] != predicted [{pred_item.obj_type}]"

        # Validate text ceels
        if isinstance(true_item, BaseText):
            assert isinstance(
                pred_item, BaseText
            ), f"{pred_item} is not a BaseText element, but {true_item} is."
            assert true_item.text == pred_item.text

    return True


def verify_tables(doc_pred: DsDocument, doc_true: DsDocument):
    if doc_true.tables is None:
        # No tables to check
        assert doc_pred.tables is None, "not expecting any table on this document"
        return True

    assert doc_pred.tables is not None, "no tables predicted, but expected in doc_true"

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

        assert true_item.data is not None, "documents are expected to have table data"
        assert pred_item.data is not None, "documents are expected to have table data"
        for i, row in enumerate(true_item.data):
            for j, col in enumerate(true_item.data[i]):

                # print("true: ", true_item.data[i][j])
                # print("pred: ", pred_item.data[i][j])

                assert (
                    true_item.data[i][j].text == pred_item.data[i][j].text
                ), "table-cell does not have the same text"

                assert (
                    true_item.data[i][j].obj_type == pred_item.data[i][j].obj_type
                ), "table-cell does not have the same type"

    return True


def verify_output(doc_pred: DsDocument, doc_true: DsDocument):

    assert verify_maintext(doc_pred, doc_true), "verify_maintext(doc_pred, doc_true)"
    assert verify_tables(doc_pred, doc_true), "verify_tables(doc_pred, doc_true)"

    return True


def verify_md(doc_pred_md, doc_true_md):
    return doc_pred_md == doc_true_md


def verify_dt(doc_pred_dt, doc_true_dt):
    return doc_pred_dt == doc_true_dt


def verify_conversion_result(
    input_path: Path, doc_result: ConversionResult, generate=False
):
    PageList = TypeAdapter(List[Page])

    assert (
        doc_result.status == ConversionStatus.SUCCESS
    ), f"Doc {input_path} did not convert successfully."

    doc_pred_pages: List[Page] = doc_result.pages
    doc_pred: DsDocument = doc_result.output
    doc_pred_md = doc_result.render_as_markdown()
    doc_pred_dt = doc_result.render_as_doctags()

    pages_path = input_path.with_suffix(".pages.json")
    json_path = input_path.with_suffix(".json")
    md_path = input_path.with_suffix(".md")
    dt_path = input_path.with_suffix(".doctags.txt")

    if generate:  # only used when re-generating truth
        with open(pages_path, "w") as fw:
            fw.write(json.dumps(doc_pred_pages, default=pydantic_encoder))

        with open(json_path, "w") as fw:
            fw.write(json.dumps(doc_pred, default=pydantic_encoder))

        with open(md_path, "w") as fw:
            fw.write(doc_pred_md)

        with open(dt_path, "w") as fw:
            fw.write(doc_pred_dt)
    else:  # default branch in test
        with open(pages_path, "r") as fr:
            doc_true_pages = PageList.validate_json(fr.read())

        with open(json_path, "r") as fr:
            doc_true: DsDocument = DsDocument.model_validate_json(fr.read())

        with open(md_path, "r") as fr:
            doc_true_md = fr.read()

        with open(dt_path, "r") as fr:
            doc_true_dt = fr.read()

        assert verify_cells(
            doc_pred_pages, doc_true_pages
        ), f"Mismatch in PDF cell prediction for {input_path}"

        # assert verify_output(
        #    doc_pred, doc_true
        # ), f"Mismatch in JSON prediction for {input_path}"

        assert verify_tables(
            doc_pred, doc_true
        ), f"verify_tables(doc_pred, doc_true) mismatch for {input_path}"

        assert verify_md(
            doc_pred_md, doc_true_md
        ), f"Mismatch in Markdown prediction for {input_path}"

        assert verify_dt(
            doc_pred_dt, doc_true_dt
        ), f"Mismatch in DocTags prediction for {input_path}"
