from abc import ABC, abstractmethod
from io import BytesIO
from pathlib import Path
from typing import Set, Union

from docling_core.types.experimental import DoclingDocument

from docling.datamodel.base_models import InputFormat


class AbstractDocumentBackend(ABC):
    @abstractmethod
    def __init__(self, path_or_stream: Union[BytesIO, Path], document_hash: str):
        self.path_or_stream = path_or_stream
        self.document_hash = document_hash

    @abstractmethod
    def is_valid(self) -> bool:
        pass

    @classmethod
    @abstractmethod
    def is_paginated(cls) -> bool:
        pass

    @abstractmethod
    def unload(self):
        if isinstance(self.path_or_stream, BytesIO):
            self.path_or_stream.close()

        self.path_or_stream = None

    @classmethod
    @abstractmethod
    def supported_formats(cls) -> Set[InputFormat]:
        pass


class DeclarativeDocumentBackend(AbstractDocumentBackend):
    """DeclarativeDocumentBackend.

    A declarative document backend is a backend that can transform to DoclingDocument
    straight without a recognition pipeline.
    """

    @abstractmethod
    def convert(self) -> DoclingDocument:
        pass
