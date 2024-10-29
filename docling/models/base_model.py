from abc import ABC, abstractmethod
from typing import Any, Iterable

from docling_core.types.doc import DoclingDocument, NodeItem

from docling.datamodel.base_models import Page
from docling.datamodel.document import ConversionResult


class BasePageModel(ABC):
    @abstractmethod
    def __call__(
        self, conv_res: ConversionResult, page_batch: Iterable[Page]
    ) -> Iterable[Page]:
        pass


class BaseEnrichmentModel(ABC):

    @abstractmethod
    def is_processable(self, doc: DoclingDocument, element: NodeItem) -> bool:
        pass

    @abstractmethod
    def __call__(
        self, doc: DoclingDocument, element_batch: Iterable[NodeItem]
    ) -> Iterable[Any]:
        pass
