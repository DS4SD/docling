from abc import ABC, abstractmethod
from typing import Iterable

from docling.datamodel.base_models import Page


class AbstractPageModel(ABC):
    @abstractmethod
    def __call__(self, page_batch: Iterable[Page]) -> Iterable[Page]:
        pass
