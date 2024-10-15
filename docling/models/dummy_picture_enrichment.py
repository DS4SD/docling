from typing import Any, Iterable

from docling_core.types.doc import DoclingDocument, NodeItem
from docling_core.types.doc.document import PictureClassificationData, PictureItem

from docling.models.base_model import BaseEnrichmentModel


class DummyPictureClassifierEnrichmentModel(BaseEnrichmentModel):

    def __init__(self, enabled: bool):
        self.enabled = enabled

    def is_processable(self, doc: DoclingDocument, element: NodeItem) -> bool:
        return self.enabled and isinstance(element, PictureItem)

    def __call__(
        self, doc: DoclingDocument, element_batch: Iterable[NodeItem]
    ) -> Iterable[Any]:
        if not self.enabled:
            return

        for element in element_batch:
            assert isinstance(element, PictureItem)
            element.data.classification = PictureClassificationData(
                provenance="dummy_classifier-0.0.1",
                predicted_class="dummy",
                confidence=0.42,
            )

            yield element
