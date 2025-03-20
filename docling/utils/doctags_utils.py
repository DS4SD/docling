from pathlib import Path
from typing import cast

from docling_core.experimental.serializer.base import SerializationResult
from docling_core.experimental.serializer.doctags import (
    DocTagsDocSerializer,
    DocTagsParams,
)
from docling_core.types.doc import DoclingDocument, Size
from docling_core.types.doc.document import DocItem, DocTagsDocument
from docling_core.types.doc.tokens import DocumentToken
from PIL import Image as PILImage


def remove_doctags_content(doctags: str, images: list[PILImage.Image]) -> str:
    dt_list = (
        doctags.removeprefix(f"<{DocumentToken.DOCUMENT.value}>")
        .removesuffix(f"\n</{DocumentToken.DOCUMENT.value}>")
        .split(f"\n<{DocumentToken.PAGE_BREAK.value}>\n")
    )
    doctags_doc = DocTagsDocument.from_doctags_and_image_pairs(
        cast(list[str | Path], dt_list), cast(list[PILImage.Image | Path], images)
    )
    doc = DoclingDocument(name="dummy")
    doc.load_from_doctags(doctags_doc)

    for idx, image in enumerate(images):
        size = Size(width=float(image.width), height=float(image.height))
        doc.add_page(page_no=idx + 1, size=size)
    dt_params = DocTagsParams(add_content=False)
    ser = DocTagsDocSerializer(params=dt_params, doc=doc)
    page_items: dict[int, list[SerializationResult]] = {}
    for item, _ in doc.iterate_items():
        if not isinstance(item, DocItem):
            continue
        page_no = cast(DocItem, item).prov[0].page_no
        if page_no in page_items:
            page_items[page_no].append(ser.serialize(item=item))
        else:
            page_items[page_no] = [ser.serialize(item=item)]
    pages = [ser.serialize_page(parts=parts) for parts in page_items.values()]

    return ser.serialize_doc(pages=pages).text
