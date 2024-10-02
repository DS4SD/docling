from pathlib import Path

from pydantic import Field

from docling.backend.docling_parse_backend import DoclingParseDocumentBackend
from docling.datamodel.document import ConversionResult
from docling.datamodel.pipeline_options import PipelineOptions, TesseractOcrOptions
from docling.document_converter import DocumentConverter

from .verify_utils import verify_conversion_result

# from tests.verify_utils import verify_conversion_result


GENERATE = False


# Debug
def save_output(pdf_path: Path, doc_result: ConversionResult, engine: str):
    r""" """
    import json
    import os

    parent = pdf_path.parent

    dict_fn = os.path.join(parent, f"{pdf_path.stem}.{engine}.json")
    with open(dict_fn, "w") as fd:
        json.dump(doc_result.render_as_dict(), fd)

    pages_fn = os.path.join(parent, f"{pdf_path.stem}.{engine}.pages.json")
    pages = [p.model_dump() for p in doc_result.pages]
    with open(pages_fn, "w") as fd:
        json.dump(pages, fd)

    doctags_fn = os.path.join(parent, f"{pdf_path.stem}.{engine}.doctags.txt")
    with open(doctags_fn, "w") as fd:
        fd.write(doc_result.render_as_doctags())

    md_fn = os.path.join(parent, f"{pdf_path.stem}.{engine}.md")
    with open(md_fn, "w") as fd:
        fd.write(doc_result.render_as_markdown())


def get_pdf_paths():
    # Define the directory you want to search
    directory = Path("./tests/data_scanned")

    # List all PDF files in the directory and its subdirectories
    pdf_files = sorted(directory.rglob("*.pdf"))
    return pdf_files


def get_converter(engine: str):
    pipeline_options = PipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options.do_cell_matching = True
    if engine == "tesserocr":
        pipeline_options.ocr_options = TesseractOcrOptions()

    converter = DocumentConverter(
        pipeline_options=pipeline_options,
        pdf_backend=DoclingParseDocumentBackend,
    )

    return converter


def test_e2e_conversions():

    pdf_paths = get_pdf_paths()

    for engine in ["easyocr", "tesserocr"]:
        print(f"Converting with ocr_engine: {engine}")
        converter = get_converter(engine)
        for pdf_path in pdf_paths:
            print(f"converting {pdf_path}")

            doc_result: ConversionResult = converter.convert_single(pdf_path)

            # # Save conversions
            # save_output(pdf_path, doc_result, engine)

            # Debug
            verify_conversion_result(
                input_path=pdf_path,
                doc_result=doc_result,
                generate=GENERATE,
                ocr_engine=engine,
            )


# if __name__ == "__main__":
#     test_e2e_conversions()
