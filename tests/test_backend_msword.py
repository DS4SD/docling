import json
import os
from pathlib import Path

from docling.backend.msword_backend import MsWordDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import (
    ConversionResult,
    InputDocument,
    SectionHeaderItem,
)
from docling.document_converter import DocumentConverter

GENERATE = False


def test_heading_levels():
    in_path = Path("tests/data/docx/word_sample.docx")
    in_doc = InputDocument(
        path_or_stream=in_path,
        format=InputFormat.DOCX,
        backend=MsWordDocumentBackend,
    )
    backend = MsWordDocumentBackend(
        in_doc=in_doc,
        path_or_stream=in_path,
    )
    doc = backend.convert()

    found_lvl_1 = found_lvl_2 = False
    for item, _ in doc.iterate_items():
        if isinstance(item, SectionHeaderItem):
            if item.text == "Let\u2019s swim!":
                found_lvl_1 = True
                assert item.level == 1
            elif item.text == "Let\u2019s eat":
                found_lvl_2 = True
                assert item.level == 2
    assert found_lvl_1 and found_lvl_2


def get_docx_paths():

    # Define the directory you want to search
    directory = Path("./tests/data/docx/")

    # List all PDF files in the directory and its subdirectories
    pdf_files = sorted(directory.rglob("*.docx"))
    return pdf_files


def get_converter():

    converter = DocumentConverter(allowed_formats=[InputFormat.DOCX])

    return converter


def verify_export(pred_text: str, gtfile: str):

    if not os.path.exists(gtfile) or GENERATE:
        with open(gtfile, "w") as fw:
            fw.write(pred_text)

        return True

    else:
        with open(gtfile, "r") as fr:
            true_text = fr.read()

        assert pred_text == true_text, "pred_itxt==true_itxt"
        return pred_text == true_text


def test_e2e_docx_conversions():

    docx_paths = get_docx_paths()
    converter = get_converter()

    for docx_path in docx_paths:
        # print(f"converting {docx_path}")

        gt_path = (
            docx_path.parent.parent / "groundtruth" / "docling_v2" / docx_path.name
        )

        conv_result: ConversionResult = converter.convert(docx_path)

        doc: DoclingDocument = conv_result.document

        pred_md: str = doc.export_to_markdown()
        assert verify_export(pred_md, str(gt_path) + ".md"), "export to md"

        pred_itxt: str = doc._export_to_indented_text(
            max_text_len=70, explicit_tables=False
        )
        assert verify_export(
            pred_itxt, str(gt_path) + ".itxt"
        ), "export to indented-text"

        pred_json: str = json.dumps(doc.export_to_dict(), indent=2)
        assert verify_export(pred_json, str(gt_path) + ".json"), "export to json"
