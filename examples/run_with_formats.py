import json
import logging
from pathlib import Path

from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import DocumentConversionInput
from docling.document_converter import (
    DocumentConverter,
    PdfFormatOption,
    WordFormatOption,
)
from docling.pipeline.simple_model_pipeline import SimpleModelPipeline
from docling.pipeline.standard_pdf_model_pipeline import StandardPdfModelPipeline

_log = logging.getLogger(__name__)

USE_EXPERIMENTAL = False

input_paths = [
    Path("tests/data/wiki_duck.html"),
    Path("tests/data/word_sample.docx"),
    Path("tests/data/lorem_ipsum.docx"),
    Path("tests/data/powerpoint_sample.pptx"),
    Path("tests/data/2206.01062.pdf"),
    # Path("tests/data/2305.03393v1-pg9-img.png"),
]
input = DocumentConversionInput.from_paths(input_paths)

## for defaults use:
# doc_converter = DocumentConverter()

## to customize use:
doc_converter = DocumentConverter(  # all of the below is optional, has internal defaults.
    formats=[
        InputFormat.PDF,
        # InputFormat.IMAGE,
        InputFormat.DOCX,
        InputFormat.HTML,
        InputFormat.PPTX,
    ],  # whitelist formats, other files are ignored.
    format_options={
        InputFormat.PDF: PdfFormatOption(
            pipeline_cls=StandardPdfModelPipeline, backend=PyPdfiumDocumentBackend
        ),  # PdfFormatOption(backend=PyPdfiumDocumentBackend),
        InputFormat.DOCX: WordFormatOption(
            pipeline_cls=SimpleModelPipeline  # , backend=MsWordDocumentBackend
        ),
        # InputFormat.IMAGE: PdfFormatOption(),
    },
)

conv_results = doc_converter.convert_batch(input)

for res in conv_results:
    out_path = Path("./scratch")
    print(
        f"Document {res.input.file.name} converted with status {res.status}."
        f"\nSaved markdown output to: {str(out_path)}"
    )
    # print(res.experimental.export_to_markdown())
    # Export Docling document format to markdown (experimental):
    with (out_path / f"{res.input.file.name}.md").open("w") as fp:
        fp.write(res.output.export_to_markdown())

    with (out_path / f"{res.input.file.name}.json").open("w") as fp:
        fp.write(json.dumps(res.output.export_to_dict()))
