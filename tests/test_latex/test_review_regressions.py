# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

from io import BytesIO

from docling_core.types.doc import ContentLayer

from docling.backend.latex_backend import LatexDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import InputDocument


def _convert(source: str):
    stream = BytesIO(source.encode())
    in_doc = InputDocument(
        path_or_stream=stream,
        format=InputFormat.LATEX,
        backend=LatexDocumentBackend,
        filename="review.tex",
    )
    return LatexDocumentBackend(in_doc=in_doc, path_or_stream=stream).convert()


def test_commented_definition_does_not_hide_body():
    doc = _convert(
        r"""\documentclass{article}
% \newcommand{\unused}{
\begin{document}
Important content.
\end{document}
"""
    )
    assert "Important content." in doc.export_to_markdown()


def test_verbatim_definition_is_preserved():
    doc = _convert(
        r"""\documentclass{article}
\begin{document}
\begin{verbatim}
\newcommand{\foo}{First}
\end{verbatim}
\end{document}
"""
    )
    assert r"\newcommand{\foo}{First}" in doc.export_to_markdown()


def test_body_definitions_are_invisible():
    declarations = [
        r"\newcommand{\term}{Defined}",
        r"\newenvironment{custom}{Start}{End}",
        r"\newtheorem{lemma}{Lemma}",
        r"\newlength{\customlength}",
        r"\newcounter{customcounter}",
        r"\newif\ifcustom",
        r"\newtheoremstyle{customstyle}{1pt}{2pt}{}{}{}{.}{1em}{}",
    ]
    doc = _convert(
        "\\documentclass{article}\\begin{document}\n"
        + "\n".join(declarations)
        + "\nVisible body.\\end{document}"
    )

    invisible = [
        item.text for item in doc.texts if item.content_layer == ContentLayer.INVISIBLE
    ]
    assert not (set(declarations) - set(invisible)), set(declarations) - set(invisible)
    markdown = doc.export_to_markdown()
    assert "Visible body." in markdown
    assert all(command not in markdown for command in declarations)


def test_math_environment_inside_formatting():
    doc = _convert(
        r"""\documentclass{article}
\begin{document}
\textbf{Before \begin{math}x\end{math} after.}
\end{document}
"""
    )
    markdown = doc.export_to_markdown()
    assert "Before" in markdown
    assert "$x$" in markdown
    assert "after." in markdown


def test_custom_macro_arguments_with_inline_math():
    doc = _convert(
        r"""\documentclass{article}
\newcommand{\pair}[2]{#1 and #2}
\begin{document}
\textbf{\pair{A}{B} $x$}
\end{document}
"""
    )
    markdown = doc.export_to_markdown()
    assert "A and B" in markdown
    assert "$x$" in markdown
    assert "#1" not in markdown
