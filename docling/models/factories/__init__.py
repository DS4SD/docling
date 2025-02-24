import logging
from functools import lru_cache

from docling.models.factories.ocr_factory import OcrFactory
from docling.models.factories.picture_description_factory import (
    PictureDescriptionFactory,
)

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_ocr_factory():
    factory = OcrFactory()
    factory.load_from_plugins()
    logger.info("Registered ocr engines: %r", factory.registered_kind)
    return factory


@lru_cache(maxsize=1)
def get_picture_description_factory():
    factory = PictureDescriptionFactory()
    factory.load_from_plugins()
    logger.info("Registered picture descriptions: %r", factory.registered_kind)
    return factory
