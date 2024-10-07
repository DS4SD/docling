from pathlib import Path

from docling.backend.msword_backend import MsWordDocumentBackend
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.base_models import (
    InputFormat,
    PdfPipelineOptions,
    PipelineOptions,
)
from docling.datamodel.document import DocumentConversionInput
from docling.document_converter import DocumentConverter, FormatOption
from docling.pipeline.simple_model_pipeline import SimpleModelPipeline
from docling.pipeline.standard_pdf_model_pipeline import StandardPdfModelPipeline

input_paths = [
    # Path("tests/data/wiki_duck.html"),
    Path("tests/data/word_sample.docx"),
    Path("tests/data/lorem_ipsum.docx"),
    Path("tests/data/powerpoint_sample.pptx"),
    # Path("tests/data/2206.01062.pdf"),
]
input = DocumentConversionInput.from_paths(input_paths)

# for defaults use:
doc_converter = DocumentConverter()

# to customize use:
# doc_converter = DocumentConverter( # all of the below is optional, has internal defaults.
#     formats=[InputFormat.PDF, InputFormat.DOCX],
#     format_options={
#         InputFormat.PDF: FormatOption(pipeline_cls=StandardPdfModelPipeline, backend=PyPdfiumDocumentBackend),
#         InputFormat.DOCX: FormatOption(pipeline_cls=SimpleModelPipeline, backend=MsWordDocumentBackend)
#     }
# )

conv_results = doc_converter.convert(input)

for res in conv_results:
    print(
        f"Document {res.input.file.name} converted with status {res.status}. Content:"
    )
    print(res.experimental.export_to_markdown())
