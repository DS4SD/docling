"""Backend to parse patents from the United States Patent Office (USPTO).

The parsers included in this module can handle patent grants pubished since 1976 and
patent applications since 2001.
The original files can be found in https://bulkdata.uspto.gov.
"""

import logging
from io import BytesIO
from pathlib import Path
from typing import Union

from docling_core.types.doc import DoclingDocument

from docling.backend.abstract_backend import DeclarativeDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import InputDocument

_log = logging.getLogger(__name__)


class PatentUsptoDocumentBackend(DeclarativeDocumentBackend):
    def __init__(self, in_doc: InputDocument, path_or_stream: Union[BytesIO, Path]):
        super().__init__(in_doc, path_or_stream)

        return

    def is_valid(self) -> bool:
        return False

    @classmethod
    def supports_pagination(cls) -> bool:
        return False

    def unload(self):
        return

    @classmethod
    def supported_formats(cls) -> set[InputFormat]:
        return {InputFormat.PATENT_USPTO}

    def convert(self) -> DoclingDocument:
        doc = DoclingDocument(name=self.file.stem or "file")

        return doc
