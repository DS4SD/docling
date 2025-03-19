from docling_core.experimental.serializer.doctags import (
    DocTagsDocSerializer,
    DocTagsParams,
)
from docling_core.types.doc import DoclingDocument
from docling_core.types.doc.document import DocTagsDocument
from PIL import Image as PILImage


def remove_doctags_content(doctags: str, image: PILImage.Image) -> str:
    doctags_doc = DocTagsDocument.from_doctags_and_image_pairs([doctags], [image])
    doc = DoclingDocument(name="dummy")
    doc.load_from_doctags(doctags_doc)
    dt_params = DocTagsParams(add_content=False)
    ser = DocTagsDocSerializer(params=dt_params, doc=doc)
    pages = [ser.serialize(item=item) for item, _ in doc.iterate_items()]
    return ser.serialize_doc(pages=pages).text
