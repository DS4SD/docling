import base64
import io

from PIL import Image as PILImage
from docling_core.experimental.serializer.doctags import (
    DocTagsDocSerializer,
    DocTagsParams,
)
from docling_core.types.doc import DoclingDocument, Size
from docling_core.types.doc.document import DocTagsDocument, ImageRef, PageItem
from pydantic import AnyUrl


def remove_doctags_content(doctags: str, image: PILImage.Image) -> str:
    def from_pil_to_base64(img: PILImage.Image) -> str:
        # Convert the image to a base64 str
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")  # Specify the format (e.g., JPEG, PNG, etc.)
        image_bytes = buffered.getvalue()

        # Encode the bytes to a Base64 string
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        return image_base64

    def from_pil_to_base64uri(img: PILImage.Image) -> AnyUrl:
        image_base64 = from_pil_to_base64(img)
        uri = AnyUrl(f"data:image/png;base64,{image_base64}")

        return uri

    doctags_doc = DocTagsDocument.from_doctags_and_image_pairs([doctags], [image])
    doc = DoclingDocument(name="dummy")
    doc.load_from_doctags(doctags_doc)
    image_ref = ImageRef(
        mimetype="image/png",
        dpi=72,
        size=Size(width=float(image.width), height=float(image.height)),
        uri=from_pil_to_base64uri(image),
    )
    page_item = PageItem(
        page_no=1,
        size=Size(width=float(image.width), height=float(image.height)),
        image=image_ref,
    )

    doc.pages[1] = page_item
    dt_params = DocTagsParams(add_content=False)
    ser = DocTagsDocSerializer(params=dt_params, doc=doc)
    pages = [ser.serialize(item=item) for item, _ in doc.iterate_items()]
    return ser.serialize_doc(pages=pages).text
