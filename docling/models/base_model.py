from abc import ABC, abstractmethod
from typing import Any, Generic, Iterable, Optional

from docling_core.types.doc import DoclingDocument, NodeItem, TextItem
from typing_extensions import TypeVar

from docling.datamodel.base_models import ItemAndImageEnrichmentElement, Page
from docling.datamodel.document import ConversionResult


class BasePageModel(ABC):
    @abstractmethod
    def __call__(
        self, conv_res: ConversionResult, page_batch: Iterable[Page]
    ) -> Iterable[Page]:
        pass


EnrichElementT = TypeVar("EnrichElementT", default=NodeItem)


class GenericEnrichmentModel(ABC, Generic[EnrichElementT]):

    @abstractmethod
    def is_processable(self, doc: DoclingDocument, element: NodeItem) -> bool:
        pass

    @abstractmethod
    def prepare_element(
        self, conv_res: ConversionResult, element: NodeItem
    ) -> Optional[EnrichElementT]:
        pass

    @abstractmethod
    def __call__(
        self, doc: DoclingDocument, element_batch: Iterable[EnrichElementT]
    ) -> Iterable[NodeItem]:
        pass


class BaseEnrichmentModel(GenericEnrichmentModel[NodeItem]):

    def prepare_element(
        self, conv_res: ConversionResult, element: NodeItem
    ) -> Optional[NodeItem]:
        if self.is_processable(doc=conv_res.document, element=element):
            return element
        return None


class BaseItemAndImageEnrichmentModel(
    GenericEnrichmentModel[ItemAndImageEnrichmentElement]
):

    images_scale: float

    def prepare_element(
        self, conv_res: ConversionResult, element: NodeItem
    ) -> Optional[ItemAndImageEnrichmentElement]:
        if not self.is_processable(doc=conv_res.document, element=element):
            return None

        assert isinstance(element, TextItem)
        element_prov = element.prov[0]
        page_ix = element_prov.page_no - 1
        cropped_image = conv_res.pages[page_ix].get_image(
            scale=self.images_scale, cropbox=element_prov.bbox
        )
        return ItemAndImageEnrichmentElement(item=element, image=cropped_image)
