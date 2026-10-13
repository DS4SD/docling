# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Tests for finding superscript and subscript text from PDF character geometry."""

import pytest
from docling_core.types.doc.document import Script

from docling.utils.pdf_char_geometry import PdfChar
from docling.utils.script_position import script_positions, script_runs

B, SUP, SUB = Script.BASELINE, Script.SUPER, Script.SUB


def _line(*segments, y: float = 700.0, x: float = 50.0) -> list[PdfChar]:
    """Lay out (text, size, rise) segments left to right on one baseline."""
    chars = []
    for text, size, rise in segments:
        for ch in text:
            width = 0.5 * size
            chars.append(
                PdfChar(
                    text=ch,
                    left=x,
                    bottom=y + rise - 0.2 * size,
                    right=x + width,
                    top=y + rise + 0.8 * size,
                    baseline=y + rise,
                    size=size,
                    horizontal=True,
                )
            )
            x += width
    return chars


def _runs(text: str, chars: list[PdfChar]) -> list[tuple[str, Script]]:
    runs = script_runs(text, chars, script_positions(chars))
    assert runs is not None
    return [(r.text, r.script) for r in runs]


def _marked(chars: list[PdfChar]) -> str:
    """Render the positions found as <sup>/<sub> markup, ignoring spaces."""
    out = ""
    for char, script in zip(chars, script_positions(chars)):
        if char.text.isspace():
            continue
        out += (
            char.text
            if script == B
            else f"<{script.value}>{char.text}</{script.value}>"
        )
    return out.replace("</super><super>", "").replace("</sub><sub>", "")


@pytest.mark.parametrize(
    "segments, expected",
    [
        pytest.param(
            [("E = mc", 12, 0), ("2", 7, 4.5)], "E=mc<super>2</super>", id="exponent"
        ),
        pytest.param(
            [("H", 12, 0), ("2", 7, -2.5), ("O", 12, 0)], "H<sub>2</sub>O", id="formula"
        ),
        pytest.param(
            # Word lowers a subscript by under a tenth of the font size.
            [("CO", 12, 0), ("2", 7, -1.1), (" gas", 12, 0)],
            "CO<sub>2</sub>gas",
            id="word-subscript",
        ),
        pytest.param(
            [("the 1", 12, 0), ("st", 7, 4.5), (" of May", 12, 0)],
            "the1<super>st</super>ofMay",
            id="ordinal",
        ),
        pytest.param(
            [("as shown", 12, 0), ("1,2\u20134", 7, 4.5), (". Next", 12, 0)],
            "asshown<super>1,2\u20134</super>.Next",
            id="citation",
        ),
        pytest.param(
            [("3", 6, 3), ("This footnote", 9, 0)],
            "<super>3</super>Thisfootnote",
            id="footnote-marker-first",
        ),
        pytest.param(
            [("Author", 12, 0), ("*", 7, 4.5), (" and", 12, 0)],
            "Author<super>*</super>and",
            id="footnote-mark",
        ),
    ],
)
def test_marks_scripts(segments, expected):
    assert _marked(_line(*segments)) == expected


@pytest.mark.parametrize(
    "segments",
    [
        # Drawn high but full size: not a script.
        pytest.param([("grew 12% at 25\u00b0C", 12, 0)], id="percent-degree"),
        # Smaller but on the baseline.
        pytest.param(
            [("S", 12, 0), ("MALL ", 9, 0), ("C", 12, 0), ("APS", 9, 0)],
            id="small-caps",
        ),
        # Shifted but full size.
        pytest.param(
            [("baseline ", 12, 0), ("jitter", 12, 1.5), (" here", 12, 0)],
            id="wavy-baseline",
        ),
        # A symbol font drawn small and raised.
        pytest.param(
            [("Concepts", 12, 0), ("\u2192", 7, 2), ("Docs", 12, 0)], id="arrow"
        ),
        # The raised A of the LaTeX logo sits inside the word.
        pytest.param([("L", 12, 0), ("A", 8, 3), ("TeX", 12, 0)], id="latex-logo"),
        # A drop cap is set larger and lower than the line it starts.
        pytest.param([("T", 36, -24), ("his line goes on", 12, 0)], id="drop-cap"),
    ],
)
def test_leaves_other_text_alone(segments):
    chars = _line(*segments)
    assert all(script == B for script in script_positions(chars))


def test_small_text_away_from_body_is_not_a_script():
    chars = _line(("Report 2024", 12, 0)) + _line(("page 3", 7, 4.5), x=400.0)
    assert all(script == B for script in script_positions(chars))


def test_measures_each_line_against_its_own_baseline():
    chars = _line(("x", 12, 0), ("2", 7, 4.5), y=700.0) + _line(
        ("H", 12, 0), ("2", 7, -2.5), ("O", 12, 0), y=680.0
    )
    assert _marked(chars) == "x<super>2</super>H<sub>2</sub>O"


def test_stacked_sub_and_superscript():
    chars = _line(("x", 12, 0), ("i", 7, -2.5))
    chars += _line(("2", 7, 4.5), x=chars[-1].left)
    assert script_positions(chars) == [B, SUB, SUP]


def test_runs_drop_the_space_the_pdf_does_not_have():
    chars = _line(("E = mc", 12, 0), ("2", 7, 4.5), (" in 1905.", 12, 0))
    assert _runs("E = mc 2 in 1905.", chars) == [
        ("E = mc", B),
        ("2", SUP),
        (" in 1905.", B),
    ]


def test_runs_keep_a_space_the_pdf_has():
    chars = _line(("agrees ", 12, 0), ("12", 7, 4.5))
    assert _runs("agrees 12", chars) == [("agrees ", B), ("12", SUP)]


def test_runs_match_through_ligatures_and_dashes():
    chars = _line(("\ufb01rst", 12, 0), ("1\u20132", 7, 4.5))
    assert _runs("first1-2", chars) == [("first", B), ("1-2", SUP)]


def test_runs_point_to_their_characters():
    chars = _line(("H", 12, 0), ("2", 7, -2.5), ("O", 12, 0))
    runs = script_runs("H2O", chars, script_positions(chars))
    assert runs is not None
    assert [r.chars for r in runs] == [(0,), (1,), (2,)]


def test_no_runs_without_scripts_or_when_text_does_not_match():
    plain = _line(("plain text", 12, 0))
    assert script_runs("plain text", plain, script_positions(plain)) is None
    chars = _line(("E = mc", 12, 0), ("2", 7, 4.5))
    assert (
        script_runs("something else entirely", chars, script_positions(chars)) is None
    )
