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


def get_xlsx_paths():

    # Define the directory you want to search
    directory = Path("./tests/data/xlsx/")

    # List all PDF files in the directory and its subdirectories
    pdf_files = sorted(directory.rglob("*.xlsx"))
    return pdf_files


def get_converter():

    converter = DocumentConverter(allowed_formats=[InputFormat.XLSX])

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


def test_e2e_xlsx_conversions():

    xlsx_paths = get_xlsx_paths()
    converter = get_converter()

    for xlsx_path in xlsx_paths:
        # print(f"converting {xlsx_path}")

        gt_path = (
            xlsx_path.parent.parent / "groundtruth" / "docling_v2" / xlsx_path.name
        )

        conv_result: ConversionResult = converter.convert(xlsx_path)

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
