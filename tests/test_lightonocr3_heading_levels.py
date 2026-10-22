# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

from pathlib import PurePath
from types import SimpleNamespace

import pytest
from docling_core.types.doc import SectionHeaderItem, Size

from docling.datamodel.base_models import Page, PagePredictions, VlmPrediction
from docling.datamodel.pipeline_options import VlmConvertOptions, VlmPipelineOptions
from docling.pipeline.vlm_pipeline import VlmPipeline
from docling.utils.lightonocr_utils import parse_lightonocr_markdown

_SIZE = Size(width=600, height=800)


@pytest.mark.parametrize("depth", [1, 2])
def test_standalone_heading_levels_keep_source_depths_distinct(depth: int) -> None:
    source = (
        f"![text](100,100,900,200) {'#' * depth} Parent\n"
        f"![text](100,300,900,400) {'#' * (depth + 1)} Child\n"
    )
    doc = parse_lightonocr_markdown(source, _SIZE, page_no=2)
    assert [
        item.level for item in doc.texts if isinstance(item, SectionHeaderItem)
    ] == [
        1,
        2,
    ]
    assert doc.export_to_markdown() == "## Parent\n\n### Child"
    assert all(item.prov[0].page_no == 2 for item in doc.texts)


@pytest.mark.parametrize("has_depth_one", [False, True])
def test_pipeline_normalizes_heading_levels_once_across_pages(
    has_depth_one: bool,
) -> None:
    pipeline = VlmPipeline.__new__(VlmPipeline)
    pipeline.pipeline_options = VlmPipelineOptions(
        vlm_options=VlmConvertOptions.from_preset("lightonocr3_08b")
    )
    pipeline.force_backend_text = False
    conv_res = SimpleNamespace(
        input=SimpleNamespace(file=PurePath("test.pdf")), errors=[]
    )
    first = "![text](100,100,900,200) # Chapter\n" if has_depth_one else ""
    pages = []
    for page_no, source in (
        (1, first + "![title](100,300,900,400) ## Section"),
        (2, "![title](100,100,900,200) ## Next section"),
    ):
        page = Page(
            page_no=page_no,
            size=_SIZE,
            predictions=PagePredictions(vlm_response=VlmPrediction(text=source)),
        )
        pages.append((page_no, pipeline._finalize_page_document(conv_res, page)))
    document = pipeline._join_page_documents(pages)
    headings = [item for item in document.texts if isinstance(item, SectionHeaderItem)]
    expected = [(1, 1), (1, 2), (2, 2)] if has_depth_one else [(1, 1), (2, 1)]
    assert [(item.prov[0].page_no, item.level) for item in headings] == expected
    assert document.export_to_markdown() == (
        "## Chapter\n\n### Section\n\n### Next section"
        if has_depth_one
        else "## Section\n\n## Next section"
    )
    assert not conv_res.errors
