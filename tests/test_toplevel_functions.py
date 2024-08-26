import glob
import json
from pathlib import Path

from docling.backend.docling_parse_backend import DoclingParseDocumentBackend
from docling.datamodel.base_models import ConversionStatus, PipelineOptions
from docling.document_converter import DocumentConverter

GENERATE = False


def get_pdf_paths():

    # Define the directory you want to search
    directory = Path("./tests/data")

    # List all PDF files in the directory and its subdirectories
    pdf_files = sorted(directory.rglob("*.pdf"))
    return pdf_files


def verify_json(doc_pred_json, doc_true_json):

    if doc_pred_json.keys() != doc_true_json.keys():
        return False

    if doc_pred_json["output"].keys() != doc_true_json["output"].keys():
        return False

    for l, true_item in enumerate(doc_true_json["output"]["main_text"]):
        if "text" in true_item:

            pred_item = doc_pred_json["output"]["main_text"][l]

            assert "text" in pred_item, f"`text` is in {pred_item}"
            assert true_item["text"] == pred_item["text"]

    for l, true_item in enumerate(doc_true_json["output"]["tables"]):
        if "data" in true_item:

            pred_item = doc_pred_json["output"]["tables"][l]

            assert "data" in pred_item, f"`data` is in {pred_item}"
            assert len(true_item["data"]) == len(
                pred_item["data"]
            ), "table does not have the same #-rows"
            assert len(true_item["data"][0]) == len(
                pred_item["data"][0]
            ), "table does not have the same #-cols"

            for i, row in enumerate(true_item["data"]):
                for j, col in enumerate(true_item["data"][i]):

                    if "text" in true_item["data"][i][j]:
                        assert (
                            "text" in pred_item["data"][i][j]
                        ), "table-cell does not contain text"
                        assert (
                            true_item["data"][i][j]["text"]
                            == pred_item["data"][i][j]["text"]
                        ), "table-cell does not have the same text"

    return True


def verify_md(doc_pred_md, doc_true_md):
    return doc_pred_md == doc_true_md


def test_conversions():

    pdf_paths = get_pdf_paths()
    # print(f"#-documents: {pdf_paths}")

    pipeline_options = PipelineOptions()
    pipeline_options.do_ocr = False
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options.do_cell_matching = True

    converter = DocumentConverter(
        pipeline_options=pipeline_options,
        pdf_backend=DoclingParseDocumentBackend,
    )

    for path in pdf_paths:

        doc_pred_json = None
        doc_true_json = None

        try:
            # print(f"converting {path}")
            doc_pred_json = converter.convert_single(path)
        except:
            continue

        doc_pred_md = doc_pred_json.render_as_markdown()

        json_path = path.with_suffix(".json")
        md_path = path.with_suffix(".md")

        if GENERATE:

            with open(json_path, "w") as fw:
                fw.write(doc_pred_json.model_dump_json()())

            with open(md_path, "w") as fw:
                fw.write(doc_pred_md)

        else:

            with open(json_path, "r") as fr:
                doc_true_json = json.load(fr)

            with open(md_path, "r") as fr:
                doc_true_md = "".join(fr.readlines())

            doc_ = json.loads(doc_pred_json.model_dump_json())
            # print(json.dumps(doc_, indent=2))

            assert verify_json(
                doc_, doc_true_json
            ), f"failed json prediction for {path}"

            assert verify_md(
                doc_pred_md, doc_true_md
            ), f"failed md prediction for {path}"
