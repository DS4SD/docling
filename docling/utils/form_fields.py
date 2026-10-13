# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Helpers shared by the form-field stage and the reading order."""


def without_whitespace(text: str) -> str:
    """The text with all whitespace removed.

    Printed text equals a widget's painted value when both agree without
    whitespace: the layout may split or join the painted characters.
    """
    return "".join(text.split())
