from abc import ABC, abstractmethod
from typing import Any, Iterable

from docling_core.types.experimental import DoclingDocument, NodeItem

from docling.datamodel.base_models import Page


class AbstractPageModel(ABC):
    @abstractmethod
    def __call__(self, page_batch: Iterable[Page]) -> Iterable[Page]:
        pass


class AbstractEnrichmentModel(ABC):
    @abstractmethod
    def __call__(
        self, doc: DoclingDocument, elements: Iterable[NodeItem]
    ) -> Iterable[Any]:
        pass
