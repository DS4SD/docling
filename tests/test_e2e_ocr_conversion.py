from pathlib import Path

from docling.backend.docling_parse_backend import DoclingParseDocumentBackend
from docling.datamodel.document import ConversionResult
from docling.datamodel.pipeline_options import PipelineOptions
from docling.document_converter import DocumentConverter

from .verify_utils import verify_conversion_result

GENERATE = False


# Debug
def save_output(pdf_path: Path, doc_result: ConversionResult):
    r"""
    """
    import json
    import os

    parent = pdf_path.parent

    dict_fn = os.path.join(parent, f"{pdf_path.stem}.json")
    with open(dict_fn, "w") as fd:
        json.dump(doc_result.render_as_dict(), fd)

    pages_fn = os.path.join(parent, f"{pdf_path.stem}.pages.json")
    pages = [p.model_dump() for p in doc_result.pages]
    with open(pages_fn, "w") as fd:
        json.dump(pages, fd)

    doctags_fn = os.path.join(parent, f"{pdf_path.stem}.doctags.txt")
    with open(doctags_fn, "w") as fd:
        fd.write(doc_result.render_as_doctags())

    md_fn = os.path.join(parent, f"{pdf_path.stem}.md")
    with open(md_fn, "w") as fd:
        fd.write(doc_result.render_as_markdown())


def get_pdf_paths():
    # TODO: Debug
    # Define the directory you want to search
    # directory = Path("./tests/data")
    directory = Path("./tests/data/scanned")

    # List all PDF files in the directory and its subdirectories
    pdf_files = sorted(directory.rglob("*.pdf"))
    return pdf_files


def get_converter():

    pipeline_options = PipelineOptions()
    # Debug
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options.do_cell_matching = True

    converter = DocumentConverter(
        pipeline_options=pipeline_options,
        pdf_backend=DoclingParseDocumentBackend,
    )

    return converter


def test_e2e_conversions():

    pdf_paths = get_pdf_paths()
    converter = get_converter()

    for pdf_path in pdf_paths:
        print(f"converting {pdf_path}")

        doc_result: ConversionResult = converter.convert_single(pdf_path)

        # Debug
        verify_conversion_result(
            input_path=pdf_path, doc_result=doc_result, generate=GENERATE
        )
