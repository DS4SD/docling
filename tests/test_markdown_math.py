# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

import pytest

from docling.utils.markdown_math import create_markdown_parser


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            "Price $5-$10 and $x$; the answer is $5$ or $2+2$.",
            "Price $5-$10 and <math>x</math>; the answer is <math>5</math> or <math>2+2</math>.",
        ),
        (
            "about ~5 m and ~10 m, where $x$ is the length",
            "about ~5 m and ~10 m, where <math>x</math> is the length",
        ),
        (
            "| A | B |\n| --- | --- |\n| $x$ | y |",
            "| A | B |\n| --- | --- |\n| <math>x</math> | y |",
        ),
        ("> [!NOTE]\n> Value $x$.", "&gt; [!NOTE]\n&gt; Value <math>x</math>."),
        (
            "See www.example.com and $x$.",
            "See www.example.com and <math>x</math>.",
        ),
    ],
)
def test_inline_math_preserves_native_text_syntax(source: str, expected: str) -> None:
    assert create_markdown_parser(inline_only=True).convert(source) == (
        f"<p>{expected}</p>\n"
    )


def test_full_markdown_still_parses_tables_with_math() -> None:
    rendered = create_markdown_parser().convert("| A | B |\n| --- | --- |\n| $x$ | y |")
    assert "<table>" in rendered
    assert "<td><math>x</math></td>" in rendered
