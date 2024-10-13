from typing import Any, Iterable

from docling_core.types.experimental import DoclingDocument, NodeItem
from docling_core.types.experimental.document import (
    PictureClassificationData,
    PictureItem,
)

from docling.models.base_model import BaseEnrichmentModel


class DummyPictureClassifierEnrichmentModel(BaseEnrichmentModel):
    def is_processable(self, doc: DoclingDocument, element: NodeItem) -> bool:
        return isinstance(element, PictureItem)

    def __call__(
        self, doc: DoclingDocument, element_batch: Iterable[NodeItem]
    ) -> Iterable[Any]:
        for element in element_batch:
            assert isinstance(element, PictureItem)
            element.data.classification = PictureClassificationData(
                provenance="dummy_classifier-0.0.1",
                predicted_class="dummy",
                confidence=0.42,
            )

            yield element
