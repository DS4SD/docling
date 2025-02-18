import logging
from functools import lru_cache

from docling.models.factories.ocr_factory import OcrFactory

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_ocr_factory():
    factory = OcrFactory()
    factory.load_from_plugins()
    # logger.info("Registered ocr engines: %r", factory.registered_kind)
    return factory
