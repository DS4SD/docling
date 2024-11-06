import logging
from pathlib import Path
from typing import Any, Iterable

from docling_core.types.doc import (
    DoclingDocument,
    NodeItem,
    PictureClassificationClass,
    PictureItem,
)
from docling_core.types.doc.document import (  # TODO: move import to docling_core.types.doc
    PictureDescriptionData,
)

from docling.datamodel.pipeline_options import PicDescBaseOptions
from docling.models.base_model import BaseEnrichmentModel


class PictureDescriptionBaseModel(BaseEnrichmentModel):

    def __init__(self, enabled: bool, options: PicDescBaseOptions):
        self.enabled = enabled
        self.options = options
        self.provenance = "TODO"

    def is_processable(self, doc: DoclingDocument, element: NodeItem) -> bool:
        # TODO: once the image classifier is active, we can differentiate among image types
        return self.enabled and isinstance(element, PictureItem)

    def _annotate_image(self, picture: PictureItem) -> PictureDescriptionData:
        raise NotImplemented

    def __call__(
        self, doc: DoclingDocument, element_batch: Iterable[NodeItem]
    ) -> Iterable[Any]:
        if not self.enabled:
            return

        for element in element_batch:
            assert isinstance(element, PictureItem)
            assert element.image is not None

            annotation = self._annotate_image(element)
            element.annotations.append(annotation)

            yield element
