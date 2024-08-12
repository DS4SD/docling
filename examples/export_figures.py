import logging
import time
from pathlib import Path
from typing import Tuple

from docling.datamodel.base_models import (
    AssembleOptions,
    ConversionStatus,
    FigureElement,
    PageElement,
    TableElement,
)
from docling.datamodel.document import ConvertedDocument, DocumentConversionInput
from docling.document_converter import DocumentConverter

_log = logging.getLogger(__name__)


def export_page_images(
    doc: ConvertedDocument,
    output_dir: Path,
):
    output_dir.mkdir(parents=True, exist_ok=True)

    doc_filename = doc.input.file.stem

    for page in doc.pages:
        page_no = page.page_no + 1
        page_image_filename = output_dir / f"{doc_filename}-{page_no}.png"
        with page_image_filename.open("wb") as fp:
            page.image.save(fp, format="PNG")


def export_element_images(
    doc: ConvertedDocument,
    output_dir: Path,
    allowed_element_types: Tuple[PageElement] = (FigureElement,),
):
    output_dir.mkdir(parents=True, exist_ok=True)

    doc_filename = doc.input.file.stem

    for element_ix, element in enumerate(doc.assembled.elements):
        if isinstance(element, allowed_element_types):
            page_ix = element.page_no
            crop_bbox = element.cluster.bbox.to_top_left_origin(
                page_height=doc.pages[page_ix].size.height
            )

            cropped_im = doc.pages[page_ix].image.crop(crop_bbox.as_tuple())
            element_image_filename = (
                output_dir / f"{doc_filename}-element-{element_ix}.png"
            )
            with element_image_filename.open("wb") as fp:
                cropped_im.save(fp, "PNG")


def main():
    logging.basicConfig(level=logging.INFO)

    input_doc_paths = [
        Path("./test/data/2206.01062.pdf"),
    ]

    input_files = DocumentConversionInput.from_paths(input_doc_paths)

    # Important: For operating with page images, we must keep them, otherwise the DocumentConverter
    # will destroy them for cleaning up memory.
    assemble_options = AssembleOptions()
    assemble_options.keep_page_images = True

    doc_converter = DocumentConverter(assemble_options=assemble_options)

    start_time = time.time()

    converted_docs = doc_converter.convert(input_files)

    for doc in converted_docs:
        if doc.status != ConversionStatus.SUCCESS:
            _log.info(f"Document {doc.input.file} failed to convert.")
            continue

        # Export page images
        export_page_images(doc, output_dir=Path("./scratch"))

        # Export figures
        # export_element_images(doc, output_dir=Path("./scratch"), allowed_element_types=(FigureElement,))

        # Export figures and tables
        export_element_images(
            doc,
            output_dir=Path("./scratch"),
            allowed_element_types=(FigureElement, TableElement),
        )

    end_time = time.time() - start_time

    _log.info(f"All documents were converted in {end_time:.2f} seconds.")


if __name__ == "__main__":
    main()
