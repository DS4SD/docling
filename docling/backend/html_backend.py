from io import BytesIO
from pathlib import Path
from typing import Set, Union

from docling_core.types.experimental import (
    DescriptionItem,
    DocItemLabel,
    DoclingDocument,
)

from docling.backend.abstract_backend import DeclarativeDocumentBackend
from docling.datamodel.base_models import InputFormat


class HTMLDocumentBackend(DeclarativeDocumentBackend):
    def __init__(self, path_or_stream: Union[BytesIO, Path], document_hash: str):
        super().__init__(path_or_stream, document_hash)

    def is_valid(self) -> bool:
        return True

    def is_paginated(cls) -> bool:
        False

    def unload(self):
        if isinstance(self.path_or_stream, BytesIO):
            self.path_or_stream.close()

        self.path_or_stream = None

    @classmethod
    def supported_formats(cls) -> Set[InputFormat]:
        return {InputFormat.HTML}

    def convert(self) -> DoclingDocument:

        # access self.path_or_stream to load stuff
        doc = DoclingDocument(description=DescriptionItem(), name="dummy")
        doc.add_text(text="I am a HTML document.", label=DocItemLabel.TEXT)
        return doc
