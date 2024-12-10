import json
import logging
import os
from io import BytesIO
from pathlib import Path

from docling_core.types.doc import DoclingDocument

from docling.datamodel.base_models import DocumentStream, InputFormat
from docling.datamodel.document import ConversionResult
from docling.document_converter import DocumentConverter

GENERATE = False


def get_pubmed_paths():
    directory = Path(os.path.dirname(__file__) + f"/data/pubmed/")
    xml_files = sorted(directory.rglob("*.xml"))
    return xml_files


def get_converter():
    converter = DocumentConverter(allowed_formats=[InputFormat.XML_PUBMED])
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


def test_e2e_pubmed_conversions(use_stream=False):
    pubmed_paths = get_pubmed_paths()
    converter = get_converter()

    for pubmed_path in pubmed_paths:
        gt_path = (
            pubmed_path.parent.parent / "groundtruth" / "docling_v2" / pubmed_path.name
        )
        if use_stream:
            buf = BytesIO(pubmed_path.open("rb").read())
            stream = DocumentStream(name=pubmed_path.name, stream=buf)
            conv_result: ConversionResult = converter.convert(stream)
        else:
            conv_result: ConversionResult = converter.convert(pubmed_path)
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


def test_e2e_pubmed_conversions_stream():
    test_e2e_pubmed_conversions(use_stream=True)


def test_e2e_pubmed_conversions_no_stream():
    test_e2e_pubmed_conversions(use_stream=False)
