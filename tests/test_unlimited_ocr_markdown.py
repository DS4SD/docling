# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Unit tests for Unlimited-OCR grounding output parsing.

These operate on plain strings: no model, no network, no reference test data.
"""

from docling_core.types.doc import Size

from docling.datamodel.pipeline_options_vlm_model import ResponseFormat
from docling.utils.deepseekocr_utils import (
    normalize_unlimited_ocr_annotations,
    parse_unlimited_ocr_markdown,
)

PAGE_SIZE = Size(width=880, height=1200)


def test_annotation_is_moved_to_ref_and_onto_its_own_line():
    raw = "<|det|>title [52, 40, 816, 63]<|/det|>Reconciliation report No. 1481"

    assert normalize_unlimited_ocr_annotations(raw) == (
        "<|ref|>title<|/ref|><|det|>[[52, 40, 816, 63]]<|/det|>\n"
        "Reconciliation report No. 1481"
    )


def test_table_markup_survives_normalization():
    raw = (
        "<|det|>table [10, 20, 30, 40]<|/det|>"
        "<table><tr><td>Total</td><td>1 245 900.50</td></tr></table>"
    )

    normalized = normalize_unlimited_ocr_annotations(raw)

    assert normalized.startswith(
        "<|ref|>table<|/ref|><|det|>[[10, 20, 30, 40]]<|/det|>\n"
    )
    assert "<table><tr><td>Total</td><td>1 245 900.50</td></tr></table>" in normalized


def test_deepseek_shaped_content_is_left_untouched():
    raw = "<|ref|>title<|/ref|><|det|>[[52, 40, 816, 63]]<|/det|>\nAlready normalized"

    assert normalize_unlimited_ocr_annotations(raw) == raw


def test_content_without_annotations_is_left_untouched():
    raw = "Plain text without any layout annotations"

    assert normalize_unlimited_ocr_annotations(raw) == raw


def test_parse_builds_document_with_heading_and_table():
    raw = (
        "<|det|>title [52, 40, 816, 63]<|/det|>Reconciliation report No. 1481\n"
        "<|det|>text [52, 71, 411, 87]<|/det|>Period: 01.04.2026 to 30.06.2026\n"
        "<|det|>table [51, 216, 601, 420]<|/det|>"
        "<table><tr><td>Date</td><td>Debit</td></tr>"
        "<tr><td>05.04.2026</td><td>184 320.00</td></tr></table>"
    )

    doc = parse_unlimited_ocr_markdown(raw, PAGE_SIZE, page_no=1, filename="page.png")
    markdown = doc.export_to_markdown()

    assert len(doc.tables) == 1
    assert "Reconciliation report No. 1481" in markdown
    assert "184 320.00" in markdown


def test_response_format_enum_value():
    assert ResponseFormat.UNLIMITED_OCR_MARKDOWN.value == "unlimited_ocr_markdown"


def test_continuation_lines_survive_in_a_text_block():
    raw = (
        "text[[100,100,900,300]]\n"
        "First line\n"
        "Second line\n"
        "\n"
        "text[[100,400,900,500]]\n"
        "Next block\n"
    )

    doc = parse_unlimited_ocr_markdown(raw, PAGE_SIZE, page_no=1, filename="page.png")
    markdown = doc.export_to_markdown()

    assert "First line" in markdown
    assert "Second line" in markdown
    assert "Next block" in markdown
    texts = [t.text for t in doc.texts]
    assert any("First line" in t and "Second line" in t for t in texts)


def test_unlimited_ocr_continuation_lines_survive_in_a_text_block():
    raw = (
        "<|det|>text [100, 100, 900, 300]<|/det|>First line\n"
        "Second line\n"
        "\n"
        "<|det|>text [100, 400, 900, 500]<|/det|>Next block\n"
    )

    doc = parse_unlimited_ocr_markdown(raw, PAGE_SIZE, page_no=1, filename="page.png")
    texts = [t.text for t in doc.texts]

    assert len(texts) >= 2
    assert any("First line" in t and "Second line" in t for t in texts)


def test_annotation_and_blank_line_still_end_a_block():
    raw = (
        "text[[100,100,900,300]]\n"
        "First line\n"
        "Second line\n"
        "\n"
        "\n"
        "Loose trailing text\n"
        "text[[100,400,900,500]]\n"
        "Next block\n"
    )

    doc = parse_unlimited_ocr_markdown(raw, PAGE_SIZE, page_no=1, filename="page.png")
    texts = [t.text for t in doc.texts]

    assert any(t == "First line\nSecond line" for t in texts)
    assert any("Next block" in t for t in texts)
    assert not any("Loose trailing text" in t for t in texts)
