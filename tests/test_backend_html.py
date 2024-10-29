import json
import os
from pathlib import Path

from docling.backend.html_backend import HTMLDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import (
    ConversionResult,
    InputDocument,
    SectionHeaderItem,
)
from docling.document_converter import DocumentConverter

GENERATE = False


def test_heading_levels():
    in_path = Path("tests/data/html/wiki_duck.html")
    in_doc = InputDocument(
        path_or_stream=in_path,
        format=InputFormat.HTML,
        backend=HTMLDocumentBackend,
    )
    backend = HTMLDocumentBackend(
        in_doc=in_doc,
        path_or_stream=in_path,
    )
    doc = backend.convert()

    found_lvl_2 = found_lvl_3 = False
    for item, _ in doc.iterate_items():
        if isinstance(item, SectionHeaderItem):
            if item.text == "Etymology":
                found_lvl_2 = True
                assert item.level == 2
            elif item.text == "Feeding":
                found_lvl_3 = True
                assert item.level == 3
    assert found_lvl_2 and found_lvl_3


def get_html_paths():

    # Define the directory you want to search
    directory = Path("./tests/data/html/")

    # List all PDF files in the directory and its subdirectories
    html_files = sorted(directory.rglob("*.html"))
    return html_files


def get_converter():

    converter = DocumentConverter(allowed_formats=[InputFormat.HTML])

    return converter


def verify_export(pred_text: str, gtfile: str):

    if not os.path.exists(gtfile) or GENERATE:
        with open(gtfile, "w") as fw:
            fw.write(pred_text)

        return True

    else:
        with open(gtfile, "r") as fr:
            true_text = fr.read()

        assert pred_text == true_text, f"pred_text!=true_text for {gtfile}"
        return pred_text == true_text


def test_e2e_html_conversions():

    html_paths = get_html_paths()
    converter = get_converter()

    for html_path in html_paths:
        # print(f"converting {html_path}")

        gt_path = (
            html_path.parent.parent / "groundtruth" / "docling_v2" / html_path.name
        )

        conv_result: ConversionResult = converter.convert(html_path)

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
