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


def verify_tables(doc_pred: DsDocument, doc_true: DsDocument):
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

    pages_path = input_path.with_suffix(".pages.json")
    json_path = input_path.with_suffix(".json")
    md_path = input_path.with_suffix(".md")

    if generate:  # only used when re-generating truth
        with open(pages_path, "w") as fw:
            fw.write(json.dumps(doc_pred_pages, default=pydantic_encoder))

        with open(json_path, "w") as fw:
            fw.write(json.dumps(doc_pred, default=pydantic_encoder))

        with open(md_path, "w") as fw:
            fw.write(doc_pred_md)
    else:  # default branch in test
        with open(pages_path, "r") as fr:
            doc_true_pages = PageList.validate_json(fr.read())

        with open(json_path, "r") as fr:
            doc_true = DsDocument.model_validate_json(fr.read())

        with open(md_path, "r") as fr:
            doc_true_md = fr.read()

        assert verify_cells(
            doc_pred_pages, doc_true_pages
        ), f"Mismatch in PDF cell prediction for {input_path}"

        assert verify_output(
            doc_pred, doc_true
        ), f"Mismatch in JSON prediction for {input_path}"

        assert verify_md(
            doc_pred_md, doc_true_md
        ), f"Mismatch in Markdown prediction for {input_path}"
