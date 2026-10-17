# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Backend for iCalendar files (RFC 5545): events, tasks, journal entries and free/busy."""

import codecs
from io import BytesIO
from pathlib import Path
from typing import Optional, Union

from docling_core.types.doc import DoclingDocument, DocumentOrigin

from docling.backend.abstract_backend import DeclarativeDocumentBackend
from docling.backend.calendar.parser import (
    Component,
    parse_components,
    unfold_bytes,
    unfold_text,
)
from docling.backend.calendar.render import add_calendar_components
from docling.datamodel.backend_options import CalendarBackendOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import InputDocument
from docling.exceptions import DocumentLoadError
from docling.utils.text_decoding import decode_text

_WIDE_BOMS = (
    codecs.BOM_UTF32_LE,
    codecs.BOM_UTF32_BE,
    codecs.BOM_UTF16_LE,
    codecs.BOM_UTF16_BE,
)
_FOLD_SAMPLE = "\r\n \t"
_CALENDAR_ROOTS = frozenset({"VCALENDAR", "VEVENT", "VTODO", "VJOURNAL", "VFREEBUSY"})


def _read_calendar_text(
    path_or_stream: Union[BytesIO, Path], encoding: Optional[str]
) -> str:
    """Decode the file with its folded lines joined.

    Folds are removed from the bytes first, because RFC 5545 lets a fold fall
    inside a multi-byte UTF-8 character. That only works when line breaks and
    spaces are single ASCII bytes, so UTF-16/32 input is decoded first.
    """
    raw = (
        path_or_stream.getvalue()
        if isinstance(path_or_stream, BytesIO)
        else path_or_stream.read_bytes()
    )
    ascii_compatible = not raw.startswith(_WIDE_BOMS)
    if encoding is not None:
        try:
            ascii_compatible = _FOLD_SAMPLE.encode(encoding) == _FOLD_SAMPLE.encode()
        except LookupError:
            pass  # decode_text reports the unknown codec
    if ascii_compatible:
        return decode_text(BytesIO(unfold_bytes(raw)), encoding)
    return unfold_text(decode_text(BytesIO(raw), encoding))


class CalendarDocumentBackend(DeclarativeDocumentBackend):
    components: list[Component]

    def __init__(
        self,
        in_doc: "InputDocument",
        path_or_stream: Union[BytesIO, Path],
        options: Optional[CalendarBackendOptions] = None,
    ):
        if options is None:
            options = CalendarBackendOptions()
        super().__init__(in_doc, path_or_stream, options)

        try:
            self.components = parse_components(
                _read_calendar_text(path_or_stream, options.encoding)
            )
        except DocumentLoadError:
            raise
        except Exception as e:
            raise DocumentLoadError(
                f"CalendarDocumentBackend could not load document with hash {self.document_hash}"
            ) from e
        if not any(c.name in _CALENDAR_ROOTS for c in self.components):
            raise DocumentLoadError(
                "The document holds no calendar component (BEGIN:VCALENDAR or "
                "BEGIN:VEVENT, VTODO, VJOURNAL, VFREEBUSY)."
            )
        self.valid = True

    def is_valid(self) -> bool:
        return self.valid

    @classmethod
    def supports_pagination(cls) -> bool:
        return False

    def unload(self):
        if isinstance(self.path_or_stream, BytesIO):
            self.path_or_stream.close()
        self.path_or_stream = None

    @classmethod
    def supported_formats(cls) -> set[InputFormat]:
        return {InputFormat.CALENDAR}

    def convert(self) -> DoclingDocument:
        origin = DocumentOrigin(
            filename=self.file.name or "file.ics",
            mimetype="text/calendar",
            binary_hash=self.document_hash,
        )
        doc = DoclingDocument(name=self.file.stem or "file", origin=origin)
        add_calendar_components(doc, self.components)
        return doc
