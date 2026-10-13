# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""End-to-end tests for superscript and subscript recovery in the PDF pipeline."""

from pathlib import Path

import pytest
from docling_core.types.doc.document import InlineGroup, Script, TextItem

from docling.backend.docling_parse_backend import ThreadedDoclingParseDocumentBackend
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    ScriptPositionOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption

pytestmark = pytest.mark.ml_pdf_model

# Exported from Word-style formatting (LibreOffice), with an embedded font.
_PDF = Path("tests/data/pdf/script_position.pdf")


def _convert(backend, enabled: bool):
    options = PdfPipelineOptions(do_ocr=False, do_table_structure=False)
    options.script_position_options = ScriptPositionOptions(enabled=enabled)
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=options, backend=backend)
        }
    )
    return converter.convert(_PDF).document


def _runs(document) -> list[list[tuple[str, Script]]]:
    out = []
    for group in document.groups:
        if not isinstance(group, InlineGroup):
            continue
        runs = []
        for ref in group.children:
            item = ref.resolve(document)
            script = item.formatting.script if item.formatting else Script.BASELINE
            runs.append((item.text, script))
        out.append(runs)
    return out


def _scripts(runs) -> list[tuple[str, Script]]:
    return [
        (text.strip(), script)
        for group in runs
        for text, script in group
        if script != Script.BASELINE
    ]


def test_marks_superscript_and_subscript_runs():
    document = _convert(ThreadedDoclingParseDocumentBackend, enabled=True)
    runs = _runs(document)
    assert _scripts(runs) == [
        ("2", Script.SUPER),
        ("2", Script.SUB),
        ("2", Script.SUB),
        ("st", Script.SUPER),
        ("rd", Script.SUPER),
        ("[12]", Script.SUPER),
    ]
    # The space the text-line builder puts before a script ("mc 2") is gone.
    assert runs[0][:2] == [
        ("Einstein wrote E = mc", Script.BASELINE),
        ("2", Script.SUPER),
    ]
    # A line without scripts stays a plain text item.
    assert any(
        isinstance(item, TextItem) and item.text.startswith("Plain line")
        for item in document.texts
    )


def test_marks_scripts_with_the_pypdfium2_backend():
    document = _convert(PyPdfiumDocumentBackend, enabled=True)
    # This backend puts the "2" of "mc2" in a text item of its own, so it has no line to
    # be measured against.
    assert _scripts(_runs(document)) == [
        ("2", Script.SUB),
        ("2", Script.SUB),
        ("st", Script.SUPER),
        ("rd", Script.SUPER),
        ("[12]", Script.SUPER),
    ]


def test_disabled_leaves_the_document_unchanged():
    document = _convert(ThreadedDoclingParseDocumentBackend, enabled=False)
    assert not _runs(document)
    assert "E = mc 2 in 1905." in document.export_to_markdown()
