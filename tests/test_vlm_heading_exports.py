# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Heading depth must survive VLM response parsing and Markdown export."""

import pytest
from docling_core.types.doc import (
    DocItemLabel,
    DoclingDocument,
    SectionHeaderItem,
    Size,
)

from docling.utils.chandra_utils import _add_html_fragment, parse_chandra_html
from docling.utils.nemotron_parse_utils import parse_nemotron_parse_v2


@pytest.mark.parametrize("parser", ["chandra", "nemotron", "html_fragment"])
@pytest.mark.parametrize("depth", [2, 3, 6])
def test_heading_depth_survives_export(parser: str, depth: int) -> None:
    size = Size(width=600, height=800)
    html = (
        '<div data-bbox="100 100 900 200" data-label="Section-Header">'
        f"<h{depth}>Method</h{depth}></div>"
    )
    if parser == "chandra":
        doc = parse_chandra_html(html, size, page_no=2)
    elif parser == "nemotron":
        source = (
            f"<x_0.2><y_0.2>{'#' * depth} Method<x_0.8><y_0.4><class_Section-header>"
        )
        doc = parse_nemotron_parse_v2(source, size, size, page_no=2)
    else:
        doc = DoclingDocument(name="fragment")
        doc.add_page(page_no=2, size=size)
        _add_html_fragment(doc, html, label=DocItemLabel.TEXT)

    item = doc.texts[0]
    assert isinstance(item, SectionHeaderItem)
    assert item.level == depth - 1
    assert item.prov[0].page_no == 2
    assert doc.export_to_markdown() == f"{'#' * depth} Method"


def test_formatted_html_heading_keeps_one_coordinate_owner() -> None:
    doc = parse_chandra_html(
        '<div data-bbox="100 100 900 200" data-label="Section-Header">'
        "<h3><b>Method</b> and results</h3></div>",
        Size(width=600, height=800),
        page_no=1,
    )
    assert isinstance(doc.texts[0], SectionHeaderItem)
    assert doc.texts[0].level == 2
    assert doc.texts[0].prov
    assert all(not item.prov for item in doc.texts[1:])
    assert doc.export_to_markdown() == "### **Method** and results"
