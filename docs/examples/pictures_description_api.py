import logging
from pathlib import Path

from docling_core.types.doc import PictureItem

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    PictureDescriptionApiOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption


def main():
    logging.basicConfig(level=logging.INFO)

    input_doc_path = Path("./tests/data/pdf/2206.01062.pdf")

    # This is using a local API server to do picture description.
    # For example, you can launch it locally with:
    # $ vllm serve "HuggingFaceTB/SmolVLM-256M-Instruct"

    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_picture_description = True
    pipeline_options.picture_description_options = PictureDescriptionApiOptions(
        url="http://localhost:8000/v1/chat/completions",
        params=dict(
            model="HuggingFaceTB/SmolVLM-256M-Instruct",
            seed=42,
            max_completion_tokens=200,
        ),
        prompt="Describe the image in three sentences. Be consise and accurate.",
        timeout=90,
    )

    doc_converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options,
            )
        }
    )
    result = doc_converter.convert(input_doc_path)

    for element, _level in result.document.iterate_items():
        if isinstance(element, PictureItem):
            print(
                f"Picture {element.self_ref}\n"
                f"Caption: {element.caption_text(doc=result.document)}\n"
                f"Annotations: {element.annotations}"
            )


if __name__ == "__main__":
    main()
