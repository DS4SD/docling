import json
import logging
import time
from pathlib import Path
from typing import Iterable

from docling.datamodel.base_models import (
    AssembleOptions,
    BoundingBox,
    ConversionStatus,
    CoordOrigin,
    PipelineOptions,
)
from docling.datamodel.document import ConvertedDocument, DocumentConversionInput
from docling.document_converter import DocumentConverter

_log = logging.getLogger(__name__)


def export_figures(
    converted_docs: Iterable[ConvertedDocument],
    output_dir: Path,
):
    output_dir.mkdir(parents=True, exist_ok=True)

    success_count = 0
    failure_count = 0

    for doc in converted_docs:
        if doc.status == ConversionStatus.SUCCESS:
            success_count += 1
            doc_filename = doc.input.file.stem

            for page in doc.pages:
                page_no = page.page_no + 1
                page_image_filename = output_dir / f"{doc_filename}-{page_no}.png"
                with page_image_filename.open("wb") as fp:
                    page.image.save(fp, format="PNG")

            for fig_ix, fig in enumerate(doc.output.figures):
                page_no = fig.prov[0].page
                page_ix = page_no - 1
                x0, y0, x1, y1 = fig.prov[0].bbox
                crop_bbox = BoundingBox(
                    l=x0, b=y0, r=x1, t=y1, coord_origin=CoordOrigin.BOTTOMLEFT
                ).to_top_left_origin(page_height=doc.pages[page_ix].size.height)

                cropped_im = doc.pages[page_ix].image.crop(crop_bbox.as_tuple())
                fig_image_filename = output_dir / f"{doc_filename}-fig{fig_ix+1}.png"
                with fig_image_filename.open("wb") as fp:
                    cropped_im.save(fp, "PNG")

        else:
            _log.info(f"Document {doc.input.file} failed to convert.")
            failure_count += 1

    _log.info(
        f"Processed {success_count + failure_count} docs, of which {failure_count} failed"
    )


def main():
    logging.basicConfig(level=logging.INFO)

    input_doc_paths = [
        Path("./test/data/2206.01062.pdf"),
    ]

    input_files = DocumentConversionInput.from_paths(input_doc_paths)

    assemble_options = AssembleOptions()
    assemble_options.remove_page_images = False

    doc_converter = DocumentConverter(assemble_options=assemble_options)

    start_time = time.time()

    converted_docs = doc_converter.convert(input_files)
    export_figures(converted_docs, output_dir=Path("./scratch"))

    end_time = time.time() - start_time

    _log.info(f"All documents were converted in {end_time:.2f} seconds.")


if __name__ == "__main__":
    main()
