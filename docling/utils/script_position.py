# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Find superscript and subscript text from the size and baseline of PDF characters.

A character is a superscript or subscript when it is drawn smaller than the body text of
its line and raised or lowered against the body's baseline.
"""

from __future__ import annotations

import difflib
import itertools
import statistics
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Optional, Protocol

from docling_core.types.doc.document import Script

# A script is drawn at most this share of the body size...
MAX_SCRIPT_SIZE = 0.85
# ...and shifted by at least this share of it. Word lowers a subscript by under a tenth.
MIN_SHIFT = 0.05
MIN_SHIFT_POINTS = 0.4
# Baselines this close (share of the largest size) are the same baseline.
BASELINE_TOLERANCE = 0.04
BASELINE_TOLERANCE_POINTS = 0.25
# Baseline groups at least this share of the largest size can be the body.
BODY_SIZE_RATIO = 0.9
# Largest gap (share of the body size) between a script and the text it marks.
TOUCH_GAP = 0.6
# Letters tighter than this to body letters on both sides sit inside a word ("LaTeX").
IN_WORD_GAP = 0.15
# A body of this few letters beside a longer raised run is a drop cap.
MAX_DROP_CAP = 3
# A new line starts where the pen moves left, or the baseline jumps, by this share of the size.
LINE_BACKTRACK = 0.5
LINE_JUMP = 1.2
# Marks raised as footnote references with no letter or digit.
FOOTNOTE_MARKS = frozenset("*\u2020\u2021\u00a7\u00b6\u2016#")
# Share of an item's characters that must be found among the PDF characters.
MIN_ALIGNED = 0.8
# Matching is quadratic, so longer items are skipped.
MAX_ALIGN_CHARS = 5000
# Gap (share of the size) under which two characters are set side by side.
MAX_JOIN_GAP = 0.15

_PUNCTUATION_FOLD = str.maketrans(
    {
        "\N{LEFT SINGLE QUOTATION MARK}": "'",
        "\N{RIGHT SINGLE QUOTATION MARK}": "'",
        "\N{SINGLE LOW-9 QUOTATION MARK}": "'",
        "\N{PRIME}": "'",
        "\N{LEFT DOUBLE QUOTATION MARK}": '"',
        "\N{RIGHT DOUBLE QUOTATION MARK}": '"',
        "\N{DOUBLE LOW-9 QUOTATION MARK}": '"',
        "\N{DOUBLE PRIME}": '"',
        "\N{HYPHEN}": "-",
        "\N{NON-BREAKING HYPHEN}": "-",
        "\N{FIGURE DASH}": "-",
        "\N{EN DASH}": "-",
        "\N{EM DASH}": "-",
        "\N{MINUS SIGN}": "-",
    }
)


class ScriptChar(Protocol):
    """A character as detection needs it, see ``pdf_char_geometry.PdfChar``."""

    @property
    def text(self) -> str: ...
    @property
    def left(self) -> float: ...
    @property
    def right(self) -> float: ...
    @property
    def baseline(self) -> float: ...
    @property
    def size(self) -> float: ...
    @property
    def horizontal(self) -> bool: ...


@dataclass(frozen=True)
class ScriptRun:
    """A piece of a text item's text at one script position."""

    text: str
    script: Script
    # Indexes of the PDF characters matched to the run.
    chars: tuple[int, ...]


def script_positions(chars: Sequence[ScriptChar]) -> list[Script]:
    """Return the script position of each character of one text item, in content order."""
    positions = [Script.BASELINE] * len(chars)
    for line in _split_lines(chars):
        for index, script in _line_scripts(chars, line).items():
            positions[index] = script
    return positions


def script_runs(
    text: str, chars: Sequence[ScriptChar], positions: Sequence[Script]
) -> Optional[list[ScriptRun]]:
    """Split an item's text into baseline, superscript and subscript runs.

    The text is matched to the PDF characters first, since it differs from them in
    ligatures, dashes and spaces. A space between a character and its script that the PDF
    does not have ("mc 2") is dropped. Runs keep their own whitespace. Returns None when the
    text has no script or cannot be matched.
    """
    if not any(p != Script.BASELINE for p in positions):
        return None
    mapping = _align(text, chars)
    if mapping is None:
        return None

    roles: list[Optional[Script]] = [None] * len(text)
    for index, char_index in mapping.items():
        roles[index] = positions[char_index]
    if not any(r not in (None, Script.BASELINE) for r in roles):
        return None

    solid = [i for i, ch in enumerate(text) if not ch.isspace()]
    # Unmatched characters take the position of matched neighbours that agree.
    for k, index in enumerate(solid):
        if roles[index] is not None:
            continue
        before = next(
            (roles[j] for j in reversed(solid[:k]) if roles[j] is not None), None
        )
        after = next((roles[j] for j in solid[k + 1 :] if roles[j] is not None), None)
        roles[index] = before if before == after and before else Script.BASELINE

    drop: set[int] = set()
    for left, right in itertools.pairwise(solid):
        gap = range(left + 1, right)
        if not gap:
            continue
        if roles[left] == roles[right]:
            for i in gap:
                roles[i] = roles[left]
            continue
        for i in gap:
            roles[i] = Script.BASELINE
        if (
            left in mapping
            and right in mapping
            and _set_side_by_side(chars, mapping[left], mapping[right])
        ):
            drop.update(gap)
    for i in range(len(text)):
        if roles[i] is None:  # leading or trailing whitespace
            roles[i] = Script.BASELINE

    pieces: list[tuple[str, Script, list[int]]] = []
    for i, ch in enumerate(text):
        if i in drop:
            continue
        role = roles[i]
        assert role is not None
        if not pieces or pieces[-1][1] != role:
            pieces.append(("", role, []))
        piece_text, _, piece_chars = pieces[-1]
        if i in mapping and mapping[i] not in piece_chars:
            piece_chars.append(mapping[i])
        pieces[-1] = (piece_text + ch, role, piece_chars)
    return [ScriptRun(t, role, tuple(c)) for t, role, c in pieces]


def _measurable(char: ScriptChar) -> bool:
    return char.horizontal and char.size > 0 and not char.text.isspace()


def _split_lines(chars: Sequence[ScriptChar]) -> list[list[int]]:
    """Split the measurable characters into visual lines, as lists of indexes."""
    lines: list[list[int]] = []
    line: list[int] = []
    previous: Optional[ScriptChar] = None
    for index, char in enumerate(chars):
        if not _measurable(char):
            continue
        if previous is not None and (
            previous.left - char.left > LINE_BACKTRACK * max(char.size, previous.size)
            or abs(char.baseline - previous.baseline)
            > LINE_JUMP * max(char.size, previous.size)
        ):
            lines.append(line)
            line = []
        line.append(index)
        previous = char
    if line:
        lines.append(line)
    return lines


def _baseline_groups(chars: Sequence[ScriptChar], line: list[int]) -> list[list[int]]:
    largest = max(chars[i].size for i in line)
    tolerance = max(BASELINE_TOLERANCE_POINTS, BASELINE_TOLERANCE * largest)
    groups: list[list[int]] = []
    for index in sorted(line, key=lambda i: chars[i].baseline):
        if (
            groups
            and abs(
                chars[index].baseline
                - statistics.median(chars[i].baseline for i in groups[-1])
            )
            <= tolerance
        ):
            groups[-1].append(index)
        else:
            groups.append([index])
    return groups


def _line_scripts(chars: Sequence[ScriptChar], line: list[int]) -> dict[int, Script]:
    """Find the superscript and subscript characters of one visual line."""
    if len(line) < 2:
        return {}
    groups = _baseline_groups(chars, line)
    if len(groups) < 2:
        return {}
    # The body: among the groups in the largest type, the one with the most letters.
    largest = max(chars[i].size for i in line)
    candidates = [
        group
        for group in groups
        if max(chars[i].size for i in group) >= BODY_SIZE_RATIO * largest
    ]
    body = max(
        candidates,
        key=lambda group: (sum(chars[i].text.isalnum() for i in group), len(group)),
    )
    body_size = statistics.median(chars[i].size for i in body)
    body_baseline = statistics.median(chars[i].baseline for i in body)
    min_shift = max(MIN_SHIFT_POINTS, MIN_SHIFT * body_size)

    shifted: dict[int, Script] = {}
    for index in line:
        char = chars[index]
        if char.size > MAX_SCRIPT_SIZE * body_size:
            continue
        shift = char.baseline - body_baseline
        if abs(shift) >= min_shift:
            shifted[index] = Script.SUPER if shift > 0 else Script.SUB

    body_letters = sum(chars[i].text.isalnum() for i in line if i not in shifted)
    scripts: dict[int, Script] = {}
    position = 0
    while position < len(line):
        if line[position] not in shifted:
            position += 1
            continue
        end = position
        script = shifted[line[position]]
        while end + 1 < len(line) and shifted.get(line[end + 1]) == script:
            end += 1
        run = line[position : end + 1]
        before = line[position - 1] if position > 0 else None
        after = line[end + 1] if end + 1 < len(line) else None
        if _keep_run(chars, run, before, after, shifted, body_size, body_letters):
            for index in run:
                scripts[index] = script
        position = end + 1
    return scripts


def _keep_run(
    chars: Sequence[ScriptChar],
    run: list[int],
    before: Optional[int],
    after: Optional[int],
    shifted: dict[int, Script],
    body_size: float,
    body_letters: int,
) -> bool:
    """Tell a script from other small, shifted text on the line."""
    script = shifted[run[0]]
    neighbours = []
    if before is not None:
        neighbours.append((before, chars[run[0]].left - chars[before].right))
    if after is not None:
        neighbours.append((after, chars[after].left - chars[run[-1]].right))

    # It touches the text it marks, unlike a small page number or URL further along.
    touches_body = any(
        index not in shifted and -0.5 * body_size <= gap <= TOUCH_GAP * body_size
        for index, gap in neighbours
    )
    # A subscript and a superscript stacked over one base.
    stacked = any(
        index in shifted and shifted[index] != script for index, _ in neighbours
    )
    if not (touches_body or stacked):
        return False

    # Symbol fonts (arrows, bullets) are often drawn small and off the baseline.
    text = [chars[i].text for i in run]
    if not (any(t.isalnum() for t in text) or all(t in FOOTNOTE_MARKS for t in text)):
        return False

    in_word = (
        len(neighbours) == 2
        and all(t.isalpha() for t in text)
        and all(
            index not in shifted
            and chars[index].text.isalpha()
            and gap <= IN_WORD_GAP * body_size
            for index, gap in neighbours
        )
    )
    drop_cap = len(run) > MAX_DROP_CAP and body_letters <= MAX_DROP_CAP
    return not (in_word or drop_cap)


def _folded(text: str) -> list[tuple[str, int]]:
    """Fold the non-space characters for matching, each with its index in ``text``."""
    out = []
    for index, ch in enumerate(text):
        if ch.isspace():
            continue
        # NFKC unfolds ligatures into several characters.
        for part in unicodedata.normalize("NFKC", ch).translate(_PUNCTUATION_FOLD):
            if not part.isspace():
                out.append((part, index))
    return out


def _align(text: str, chars: Sequence[ScriptChar]) -> Optional[dict[int, int]]:
    """Map the characters of ``text`` to PDF character indexes, or None if too few match."""
    ours = _folded(text)
    theirs = _folded("".join(c.text if len(c.text) == 1 else " " for c in chars))
    if not ours:
        return None
    if [a for a, _ in ours] == [b for b, _ in theirs]:
        blocks = [(0, 0, len(ours))]
    elif max(len(ours), len(theirs)) > MAX_ALIGN_CHARS:
        return None
    else:
        matcher = difflib.SequenceMatcher(
            None,
            "".join(a for a, _ in ours),
            "".join(b for b, _ in theirs),
            autojunk=False,
        )
        blocks = [tuple(block) for block in matcher.get_matching_blocks()]
    mapping: dict[int, int] = {}
    for a, b, size in blocks:
        for k in range(size):
            mapping.setdefault(ours[a + k][1], theirs[b + k][1])
    solid = sum(not ch.isspace() for ch in text)
    if len(mapping) < MIN_ALIGNED * solid:
        return None
    return mapping


def _set_side_by_side(chars: Sequence[ScriptChar], left: int, right: int) -> bool:
    """Tell whether the PDF draws two characters with no space and no gap between them."""
    if right <= left or any(c.text.isspace() for c in chars[left + 1 : right]):
        return False
    a, b = chars[left], chars[right]
    return b.left - a.right <= MAX_JOIN_GAP * max(a.size, b.size)
