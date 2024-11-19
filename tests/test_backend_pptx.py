import json
import os
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import ConversionResult
from docling.document_converter import DocumentConverter

GENERATE = False


def get_pptx_paths():

    # Define the directory you want to search
    directory = Path("./tests/data/pptx/")

    # List all PPTX files in the directory and its subdirectories
    pptx_files = sorted(directory.rglob("*.pptx"))
    return pptx_files


def get_converter():

    converter = DocumentConverter(allowed_formats=[InputFormat.PPTX])

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


def test_e2e_pptx_conversions():

    pptx_paths = get_pptx_paths()
    converter = get_converter()

    for pptx_path in pptx_paths:
        # print(f"converting {pptx_path}")

        gt_path = (
            pptx_path.parent.parent / "groundtruth" / "docling_v2" / pptx_path.name
        )

        conv_result: ConversionResult = converter.convert(pptx_path)

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
