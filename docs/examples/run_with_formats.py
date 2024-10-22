import json
import logging
from io import BytesIO
from pathlib import Path

import yaml

from docling.backend.docling_parse_backend import DoclingParseDocumentBackend
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.base_models import DocumentStream, InputFormat
from docling.document_converter import (
    DocumentConverter,
    PdfFormatOption,
    WordFormatOption,
)
from docling.pipeline.simple_pipeline import SimplePipeline
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline

_log = logging.getLogger(__name__)


def main():
    input_paths = [
        Path("tests/data/wiki_duck.html"),
        Path("tests/data/word_sample.docx"),
        Path("tests/data/word_nested.docx"),
        Path("tests/data/lorem_ipsum.docx"),
        Path("tests/data/powerpoint_sample.pptx"),
        Path("tests/data/2305.03393v1-pg9-img.png"),
        Path("tests/data/2206.01062.pdf"),
        Path("tests/data/test_01.asciidoc"),
        Path("tests/data/test_02.asciidoc"),
        Path("README.md"),
    ]

    # To read from bytes instead:
    # docs = [
    #    DocumentStream(name=f.name, stream=BytesIO(f.open("rb").read()))
    #    for f in input_paths
    # ]

    ## for defaults use:
    # doc_converter = DocumentConverter()

    ## to customize use:

    doc_converter = (
        DocumentConverter(  # all of the below is optional, has internal defaults.
            allowed_formats=[
                InputFormat.PDF,
                InputFormat.IMAGE,
                InputFormat.DOCX,
                InputFormat.HTML,
                InputFormat.PPTX,
                InputFormat.ASCIIDOC,
                InputFormat.MD,
            ],  # whitelist formats, non-matching files are ignored.
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_cls=StandardPdfPipeline,
                    backend=DoclingParseDocumentBackend,
                ),
                InputFormat.DOCX: WordFormatOption(
                    pipeline_cls=SimplePipeline  # , backend=MsWordDocumentBackend
                ),
            },
        )
    )

    conv_results = doc_converter.convert_all(input_paths)
    # conv_results = doc_converter.convert_all(docs)

    for res in conv_results:
        out_path = Path("scratch")
        print(
            f"Document {res.input.file.name} converted."
            f"\nSaved markdown output to: {str(out_path)}"
        )
        # print(res.docdocument.export_to_markdown())
        # Export Docling document format to markdowndoc:
        with (out_path / f"{res.input.file.stem}.md").open("w") as fp:
            fp.write(res.document.export_to_markdown())

        with (out_path / f"{res.input.file.stem}.json").open("w") as fp:
            fp.write(json.dumps(res.document.export_to_dict()))

        with (out_path / f"{res.input.file.stem}.yaml").open("w") as fp:
            fp.write(yaml.safe_dump(res.document.export_to_dict()))


if __name__ == "__main__":
    main()
