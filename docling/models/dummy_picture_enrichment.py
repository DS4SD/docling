from typing import Any, Iterable

from docling_core.types.experimental import DoclingDocument, NodeItem
from docling_core.types.experimental.document import BasePictureData, PictureItem

from docling.models.base_model import BaseEnrichmentModel


class DummyPictureData(BasePictureData):
    hello: str


class DummyPictureClassifierEnrichmentModel(BaseEnrichmentModel):
    def is_processable(self, doc: DoclingDocument, element: NodeItem) -> bool:
        return isinstance(element, PictureItem)

    def __call__(
        self, doc: DoclingDocument, element_batch: Iterable[NodeItem]
    ) -> Iterable[Any]:
        for element in element_batch:
            assert isinstance(element, PictureItem)
            element.data = DummyPictureData(hello="world")

            yield element
