import logging

from docling.models.base_ocr_model import BaseOcrModel
from docling.models.factories.base_factory import BaseFactory

logger = logging.getLogger(__name__)


class OcrFactory(BaseFactory[BaseOcrModel]):
    def __init__(self, *args, **kwargs):
        super().__init__("ocr_engines", *args, **kwargs)


#     def on_class_not_found(self, kind: str, *args, **kwargs):

#         raise NoSuchOcrEngine(kind, self.registered_kind)


# class NoSuchOcrEngine(Exception):
#     def __init__(self, ocr_engine_kind, known_engines=None):
#         if known_engines is None:
#             known_engines = []
#         super(NoSuchOcrEngine, self).__init__(
#             "No OCR engine found with the name '%s', known engines are: %r",
#             ocr_engine_kind,
#             [cls.__name__ for cls in known_engines],
#         )
