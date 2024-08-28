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
from docling.datamodel.document import DocumentConversionInput
from docling.document_converter import DocumentConverter

_log = logging.getLogger(__name__)

IMAGE_RESOLUTION_SCALE = 2.0


def main():
    logging.basicConfig(level=logging.INFO)

    input_doc_paths = [
        Path("./tests/data/2206.01062.pdf"),
    ]
    output_dir = Path("./scratch")

    input_files = DocumentConversionInput.from_paths(input_doc_paths)

    # Important: For operating with page images, we must keep them, otherwise the DocumentConverter
    # will destroy them for cleaning up memory.
    # This is done by setting AssembleOptions.images_scale, which also defines the scale of images.
    # scale=1 correspond of a standard 72 DPI image
    assemble_options = AssembleOptions()
    assemble_options.images_scale = IMAGE_RESOLUTION_SCALE

    doc_converter = DocumentConverter(assemble_options=assemble_options)

    start_time = time.time()

    conv_results = doc_converter.convert(input_files)

    success_count = 0
    failure_count = 0
    output_dir.mkdir(parents=True, exist_ok=True)
    for conv_res in conv_results:
        if conv_res.status != ConversionStatus.SUCCESS:
            _log.info(f"Document {conv_res.input.file} failed to convert.")
            failure_count += 1
            continue

        doc_filename = conv_res.input.file.stem

        # Export page images
        for page in conv_res.pages:
            page_no = page.page_no + 1
            page_image_filename = output_dir / f"{doc_filename}-{page_no}.png"
            with page_image_filename.open("wb") as fp:
                page.image.save(fp, format="PNG")

        # Export figures and tables
        for element, image in conv_res.render_element_images(
            element_types=(FigureElement, TableElement)
        ):
            element_image_filename = (
                output_dir / f"{doc_filename}-element-{element.id}.png"
            )
            with element_image_filename.open("wb") as fp:
                image.save(fp, "PNG")

        success_count += 1

    end_time = time.time() - start_time

    _log.info(f"All documents were converted in {end_time:.2f} seconds.")

    if failure_count > 0:
        raise RuntimeError(
            f"The example failed converting {failure_count} on {len(input_doc_paths)}."
        )


if __name__ == "__main__":
    main()
