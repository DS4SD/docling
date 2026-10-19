# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

import json

import pytest
from docling_core.types.doc import CodeItem, FormulaItem, Size

from docling.utils.dots_utils import parse_dots_json
from docling.utils.nemotron_parse_utils import parse_nemotron_parse_v2


@pytest.mark.parametrize("parser", ["dots", "nemotron"])
@pytest.mark.parametrize(
    "category", ["Text", "Title", "Section-header", "List-item", "Caption"]
)
def test_inline_math_survives_export_without_changing_block_ownership(
    parser: str, category: str
) -> None:
    latex = r"x_1 * y_2 * z_3 < 2"
    text = f"Value ${latex}$ and `literal $x_1$`; cost: \\$5."
    if category == "Section-header":
        text = "### " + text
    size = Size(width=600, height=800)
    if parser == "dots":
        source = json.dumps(
            [{"category": category, "bbox": [100, 100, 500, 200], "text": text}]
        )
        doc = parse_dots_json(source, size, page_no=2)
    else:
        source = f"<x_0.2><y_0.2>{text}<x_0.8><y_0.4><class_{category}>"
        doc = parse_nemotron_parse_v2(source, size, size, page_no=2)
    formulas = [item for item in doc.texts if isinstance(item, FormulaItem)]
    assert [formula.text for formula in formulas] == [latex]
    assert all(not formula.prov for formula in formulas)
    assert len([item for item in doc.texts if item.prov]) == 1
    assert next(item for item in doc.texts if item.prov).prov[0].page_no == 2
    assert [item.text for item in doc.texts if isinstance(item, CodeItem)] == [
        "literal $x_1$"
    ]
    exported = doc.export_to_markdown()
    assert f"${latex}$" in exported
    assert "`literal $x_1$`" in exported
    assert "$5" in exported
