from pathlib import Path
from typing import cast

from docling_core.experimental.serializer.doctags import (
    DocTagsDocSerializer,
    DocTagsParams,
)
from docling_core.types.doc import DoclingDocument, Size
from docling_core.types.doc.document import DocTagsDocument
from PIL import Image as PILImage


def remove_doctags_content(doctags: list[str], images: list[PILImage.Image]) -> str:
    doctags_doc = DocTagsDocument.from_doctags_and_image_pairs(
        cast(list[str | Path], doctags), cast(list[PILImage.Image | Path], images)
    )
    doc = DoclingDocument(name="dummy")
    doc.load_from_doctags(doctags_doc)
    for idx, image in enumerate(images):
        size = Size(width=float(image.width), height=float(image.height))
        doc.add_page(page_no=idx + 1, size=size)
    dt_params = DocTagsParams(add_content=False)
    ser = DocTagsDocSerializer(params=dt_params, doc=doc)
    items = [ser.serialize(item=item) for item, _ in doc.iterate_items()]
    dt_params = DocTagsParams(add_content=False)
    ser = DocTagsDocSerializer(params=dt_params, doc=doc)
    return ser.serialize_doc(pages=items).text
