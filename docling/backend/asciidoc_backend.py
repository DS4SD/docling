import logging
from io import BytesIO
from pathlib import Path
from typing import Set, Union

from docling_core.types.doc import (
    DocItemLabel,
    DoclingDocument,
    DocumentOrigin,
    GroupLabel,
    TableCell,
    TableData,
)

from docling.backend.abstract_backend import DeclarativeDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import InputDocument

_log = logging.getLogger(__name__)


class ASCIIDocDocumentBackend(DeclarativeDocumentBackend):

    def __init__(self, in_doc: "InputDocument", path_or_stream: Union[BytesIO, Path]):
        super().__init__(in_doc, path_or_stream)

        self.path_or_stream = path_or_stream

        self.valid = True
        
    def is_valid(self) -> bool:
        return self.valid

    @classmethod
    def supports_pagination(cls) -> bool:
        return False

    def unload(self):
        return

    @classmethod
    def supported_formats(cls) -> Set[InputFormat]:
        return {InputFormat.ASCIIDOC}

    def convert(self) -> DoclingDocument:
        """
        Parses the ASCII into a structured document model.
        """

        fname = ""
        if isinstance(self.path_or_stream, Path):
            fname = self.path_or_stream.name

        origin = DocumentOrigin(
            filename=fname,
            mimetype="asciidoc",
            binary_hash=self.document_hash,
        )
        if len(fname) > 0:
            docname = Path(fname).stem
        else:
            docname = "stream"            
        
        doc = DoclingDocument(name=docname, origin=origin)

        doc = self.parse_stream(doc)
        
        return doc

    def parse(self, doc: DoclingDocument):

        return doc
