from abc import ABC, abstractmethod
from typing import Iterable, Optional, Set

from docling_core.types.experimental import BoundingBox, Size
from PIL import Image

from docling.backend.abstract_backend import AbstractDocumentBackend
from docling.datamodel.base_models import Cell, InputFormat


class PdfPageBackend(ABC):

    @abstractmethod
    def get_text_in_rect(self, bbox: "BoundingBox") -> str:
        pass

    @abstractmethod
    def get_text_cells(self) -> Iterable["Cell"]:
        pass

    @abstractmethod
    def get_bitmap_rects(self, float: int = 1) -> Iterable["BoundingBox"]:
        pass

    @abstractmethod
    def get_page_image(
        self, scale: float = 1, cropbox: Optional["BoundingBox"] = None
    ) -> Image.Image:
        pass

    @abstractmethod
    def get_size(self) -> "Size":
        pass

    @abstractmethod
    def is_valid(self) -> bool:
        pass

    @abstractmethod
    def unload(self):
        pass


class PdfDocumentBackend(AbstractDocumentBackend):
    @abstractmethod
    def load_page(self, page_no: int) -> PdfPageBackend:
        pass

    @abstractmethod
    def page_count(self) -> int:
        pass

    @classmethod
    def supported_formats(cls) -> Set[InputFormat]:
        return {InputFormat.PDF}

    @classmethod
    def is_paginated(cls) -> bool:
        return True
