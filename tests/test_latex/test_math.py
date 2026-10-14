# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

from io import BytesIO
from pathlib import Path

import pytest
from docling_core.types.doc import DocItemLabel, GroupLabel

from docling.backend.latex_backend import LatexDocumentBackend
from docling.datamodel.backend_options import LatexBackendOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import ConversionResult, DoclingDocument, InputDocument
from docling.document_converter import DocumentConverter

from ..test_data_gen_flag import GEN_TEST_DATA
from ..verify_utils import verify_document, verify_export

GENERATE = GEN_TEST_DATA
LATEX_DATA_DIR = Path("./tests/data/latex/sources/")


def test_latex_math_parsing():
    # Test align environment (starred and unstarred) and inline/display math
    latex_content = rb"""
    \documentclass{article}
    \begin{document}
    Inline math: $E=mc^2$.
    Display math:
    $$
    x = \frac{-b \pm \sqrt{b^2-4ac}}{2a}
    $$
    Aligned equations:
    \begin{align}
    a &= b + c \\
    d &= e + f
    \end{align}
    \end{document}
    """

    in_doc = InputDocument(
        path_or_stream=BytesIO(latex_content),
        format=InputFormat.LATEX,
        backend=LatexDocumentBackend,
        filename="test.tex",
    )
    backend = LatexDocumentBackend(in_doc=in_doc, path_or_stream=BytesIO(latex_content))
    doc = backend.convert()

    formulas = [t for t in doc.texts if t.label == DocItemLabel.FORMULA]
    assert len(formulas) >= 2  # Display math and Align environment

    # Inline math should be part of the paragraph text
    paragraphs = [
        t for t in doc.texts if t.label in [DocItemLabel.PARAGRAPH, DocItemLabel.TEXT]
    ]
    full_text = " ".join([p.text for p in paragraphs])
    assert "$E=mc^2$" in full_text

    md = doc.export_to_markdown()
    # Check delimiters
    assert "$E=mc^2$" in md or r"\( E=mc^2 \)" in md
    assert r"\frac" in md
    assert r"\begin{align}" in md


def test_latex_various_math_environments():
    """Test various math environments"""
    latex_content = rb"""
    \documentclass{article}
    \begin{document}
    Equation starred:
    \begin{equation*}
    a = b
    \end{equation*}
    Gather:
    \begin{gather}
    x = y \\
    z = w
    \end{gather}
    Multline:
    \begin{multline}
    first \\
    second
    \end{multline}
    \end{document}
    """
    in_doc = InputDocument(
        path_or_stream=BytesIO(latex_content),
        format=InputFormat.LATEX,
        backend=LatexDocumentBackend,
        filename="test.tex",
    )
    backend = LatexDocumentBackend(in_doc=in_doc, path_or_stream=BytesIO(latex_content))
    doc = backend.convert()

    formulas = [t for t in doc.texts if t.label == DocItemLabel.FORMULA]
    assert len(formulas) >= 3


def test_latex_preserves_numbered_and_aligned_math_environments():
    latex_content = rb"""
    \documentclass{article}
    \begin{document}
    \begin{eqnarray}
    a&=&b\\
    c&=&d
    \end{eqnarray}
    \begin{equation}
    x=y\tag{1.2a}
    \end{equation}
    \end{document}
    """
    in_doc = InputDocument(
        path_or_stream=BytesIO(latex_content),
        format=InputFormat.LATEX,
        backend=LatexDocumentBackend,
        filename="test.tex",
    )
    backend = LatexDocumentBackend(in_doc=in_doc, path_or_stream=BytesIO(latex_content))
    formulas = [
        item.text
        for item in backend.convert().texts
        if item.label == DocItemLabel.FORMULA
    ]

    assert len(formulas) == 2
    assert formulas[0].startswith(r"\begin{eqnarray}")
    assert formulas[0].endswith(r"\end{eqnarray}")
    assert formulas[1].startswith(r"\begin{equation}")
    assert r"\tag{1.2a}" in formulas[1]


def test_latex_shortcuts_do_not_change_macro_definitions():
    latex_content = rb"""
    \documentclass{article}
    \begin{document}
    \newcommand{\be}{\begin{equation}}
    \newcommand{\ee}{\end{equation}}
    \be x=y \ee
    \end{document}
    """
    in_doc = InputDocument(
        path_or_stream=BytesIO(latex_content),
        format=InputFormat.LATEX,
        backend=LatexDocumentBackend,
        filename="test.tex",
    )
    backend = LatexDocumentBackend(in_doc=in_doc, path_or_stream=BytesIO(latex_content))
    processed = backend._preprocess_custom_macros(backend.latex_text)
    assert r"\newcommand" not in processed
    assert backend._custom_macros["be"] == r"\begin{equation}"
    assert backend._custom_macros["ee"] == r"\end{equation}"
    assert r"\begin{equation} x=y \end{equation}" in processed
    formulas = [
        item.text
        for item in backend.convert().texts
        if item.label == DocItemLabel.FORMULA
    ]
    assert len(formulas) == 1
    assert formulas[0].startswith(r"\begin{equation}")


def test_latex_expands_nested_zero_argument_macros():
    latex_content = rb"""
    \documentclass{article}
    \newcommand{\Real}{\mathbb{R}}
    \newcommand{\Rd}{\Real^d}
    \begin{document}
    The space $\Rd$ is used here.
    \end{document}
    """
    in_doc = InputDocument(
        path_or_stream=BytesIO(latex_content),
        format=InputFormat.LATEX,
        backend=LatexDocumentBackend,
        filename="test.tex",
    )
    backend = LatexDocumentBackend(in_doc=in_doc, path_or_stream=BytesIO(latex_content))
    doc = backend.convert()
    text = " ".join(item.text for item in doc.texts)
    assert r"\mathbb{R}^d" in text
    assert r"\Real" not in text


def test_latex_math_environment():
    """Test math environment (not displaymath)"""
    latex_content = rb"""
    \documentclass{article}
    \begin{document}
    Inline: \begin{math}a+b\end{math}.
    \end{document}
    """
    in_doc = InputDocument(
        path_or_stream=BytesIO(latex_content),
        format=InputFormat.LATEX,
        backend=LatexDocumentBackend,
        filename="test.tex",
    )
    backend = LatexDocumentBackend(in_doc=in_doc, path_or_stream=BytesIO(latex_content))
    doc = backend.convert()

    formulas = [t for t in doc.texts if t.label == DocItemLabel.FORMULA]
    assert len(formulas) >= 1


def test_latex_displaymath_brackets():
    """Test \\[ \\] display math"""
    latex_content = rb"""
    \documentclass{article}
    \begin{document}
    Display: \[ x^2 + y^2 = z^2 \]
    \end{document}
    """
    in_doc = InputDocument(
        path_or_stream=BytesIO(latex_content),
        format=InputFormat.LATEX,
        backend=LatexDocumentBackend,
        filename="test.tex",
    )
    backend = LatexDocumentBackend(in_doc=in_doc, path_or_stream=BytesIO(latex_content))
    doc = backend.convert()

    formulas = [t for t in doc.texts if t.label == DocItemLabel.FORMULA]
    assert len(formulas) >= 1


def test_latex_split_cases_math():
    """Test split/cases inner math environments produce FORMULA labels"""
    latex_content = rb"""
    \documentclass{article}
    \begin{document}
    \begin{equation}
    \begin{cases}
    x & \text{if } x > 0 \\
    -x & \text{otherwise}
    \end{cases}
    \end{equation}
    \end{document}
    """
    in_doc = InputDocument(
        path_or_stream=BytesIO(latex_content),
        format=InputFormat.LATEX,
        backend=LatexDocumentBackend,
        filename="test.tex",
    )
    backend = LatexDocumentBackend(in_doc=in_doc, path_or_stream=BytesIO(latex_content))
    doc = backend.convert()

    formulas = [t for t in doc.texts if t.label == DocItemLabel.FORMULA]
    assert len(formulas) >= 1
    # The cases content should be in the formula
    formula_text = " ".join(f.text for f in formulas)
    assert "cases" in formula_text or "otherwise" in formula_text
