from abc import ABC, abstractmethod
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable, Optional, Union

from PIL import Image


class PdfPageBackend(ABC):
    def __init__(self, page_obj: Any) -> object:
        pass

    @abstractmethod
    def get_text_in_rect(self, bbox: "BoundingBox") -> str:
        pass

    @abstractmethod
    def get_text_cells(self) -> Iterable["Cell"]:
        pass

    @abstractmethod
    def get_page_image(
        self, scale: int = 1, cropbox: Optional["BoundingBox"] = None
    ) -> Image.Image:
        pass

    @abstractmethod
    def get_size(self) -> "PageSize":
        pass

    @abstractmethod
    def unload(self):
        pass


class PdfDocumentBackend(ABC):
    @abstractmethod
    def __init__(self, path_or_stream: Union[BytesIO, Path]):
        pass

    @abstractmethod
    def load_page(self, page_no: int) -> PdfPageBackend:
        pass

    @abstractmethod
    def page_count(self) -> int:
        pass

    @abstractmethod
    def is_valid(self) -> bool:
        pass

    @abstractmethod
    def unload(self):
        pass
