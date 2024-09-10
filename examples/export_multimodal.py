import datetime
import logging
import time
from pathlib import Path

import pandas as pd

from docling.datamodel.base_models import AssembleOptions, ConversionStatus
from docling.datamodel.document import DocumentConversionInput
from docling.document_converter import DocumentConverter
from docling.utils.export import generate_multimodal_pages

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

    converted_docs = doc_converter.convert(input_files)

    success_count = 0
    failure_count = 0
    output_dir.mkdir(parents=True, exist_ok=True)
    for doc in converted_docs:
        if doc.status != ConversionStatus.SUCCESS:
            _log.info(f"Document {doc.input.file} failed to convert.")
            failure_count += 1
            continue

        rows = []
        for (
            content_text,
            content_md,
            content_dt,
            page_cells,
            page_segments,
            page,
        ) in generate_multimodal_pages(doc):

            dpi = page._default_image_scale * 72

            rows.append(
                {
                    "document": doc.input.file.name,
                    "hash": doc.input.document_hash,
                    "page_hash": page.page_hash,
                    "image": {
                        "width": page.image.width,
                        "height": page.image.height,
                        "bytes": page.image.tobytes(),
                    },
                    "cells": page_cells,
                    "contents": content_text,
                    "contents_md": content_md,
                    "contents_dt": content_dt,
                    "segments": page_segments,
                    "extra": {
                        "page_num": page.page_no + 1,
                        "width_in_points": page.size.width,
                        "height_in_points": page.size.height,
                        "dpi": dpi,
                    },
                }
            )
        success_count += 1

    # Generate one parquet from all documents
    df = pd.json_normalize(rows)
    now = datetime.datetime.now()
    output_filename = output_dir / f"multimodal_{now:%Y-%m-%d_%H%M%S}.parquet"
    df.to_parquet(output_filename)

    end_time = time.time() - start_time

    _log.info(f"All documents were converted in {end_time:.2f} seconds.")

    if failure_count > 0:
        raise RuntimeError(
            f"The example failed converting {failure_count} on {len(input_doc_paths)}."
        )

    # This block demonstrates how the file can be opened with the HF datasets library
    # from datasets import Dataset
    # from PIL import Image
    # multimodal_df = pd.read_parquet(output_filename)

    # # Convert pandas DataFrame to Hugging Face Dataset and load bytes into image
    # dataset = Dataset.from_pandas(multimodal_df)
    # def transforms(examples):
    #     examples["image"] = Image.frombytes('RGB', (examples["image.width"], examples["image.height"]), examples["image.bytes"], 'raw')
    #     return examples
    # dataset = dataset.map(transforms)


if __name__ == "__main__":
    main()
