# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Tests for :func:`docling.utils.text_decoding.decode_text`."""

from io import BytesIO

from docling.utils.text_decoding import decode_text


def test_explicit_utf8_drops_leading_bom_like_autodetect() -> None:
    # A UTF-8 file that starts with a byte-order mark must decode identically
    # whether the encoding is auto-detected or explicitly requested as "utf-8".
    # See https://github.com/docling-project/docling/issues/4846
    content = b"\xef\xbb\xbf# Title\nHello"

    auto = decode_text(BytesIO(content), encoding=None)
    explicit = decode_text(BytesIO(content), encoding="utf-8")

    assert not auto.startswith("﻿")
    assert not explicit.startswith("﻿")
    assert auto == explicit


def test_plain_utf8_without_bom_is_unchanged() -> None:
    # Files without a BOM must not be affected by the BOM handling.
    content = b"# Title\nHello"

    assert decode_text(BytesIO(content), encoding="utf-8") == decode_text(
        BytesIO(content), encoding=None
    )


def test_explicit_utf8_sig_keeps_behaviour() -> None:
    content = b"\xef\xbb\xbf# Title\nHello"
    assert not decode_text(BytesIO(content), encoding="utf-8-sig").startswith("﻿")
