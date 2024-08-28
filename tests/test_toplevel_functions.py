import glob
import json
from pathlib import Path, PosixPath

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


def get_converter():

    pipeline_options = PipelineOptions()
    pipeline_options.do_ocr = False
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options.do_cell_matching = True

    converter = DocumentConverter(
        pipeline_options=pipeline_options,
        pdf_backend=DoclingParseDocumentBackend,
    )

    return converter


def convert_paths(data):
    if isinstance(data, dict):
        return {k: convert_paths(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_paths(v) for v in data]
    elif isinstance(data, PosixPath):
        return str(data)
    else:
        return data


def verify_cells(doc_pred_json, doc_true_json):

    print(doc_pred_json.keys())
    print(doc_pred_json["input"].keys())

    assert len(doc_pred_json["pages"]) == len(
        doc_true_json["pages"]
    ), "pred- and true-doc do not have the same number of pages"

    for pid, page_true_item in enumerate(doc_true_json["pages"]):

        num_true_cells = len(page_true_item["cells"])
        num_pred_cells = len(doc_pred_json["pages"][pid]["cells"])

        assert (
            num_true_cells == num_pred_cells
        ), f"num_true_cells!=num_pred_cells {num_true_cells}!={num_pred_cells}"

        for cid, cell_true_item in enumerate(page_true_item["cells"]):

            cell_pred_item = doc_pred_json["pages"][pid]["cells"][cid]

            true_text = cell_true_item["text"]
            pred_text = cell_pred_item["text"]

            assert true_text == pred_text, f"{true_text}!={pred_text}"

            for _ in ["t", "b", "l", "r"]:
                true_val = round(cell_true_item["bbox"][_])
                pred_val = round(cell_pred_item["bbox"][_])

                assert (
                    pred_val == true_val
                ), f"bbox for {_} is not the same: {true_val} != {pred_val}"

    return True


def verify_maintext(doc_pred_json, doc_true_json):

    for l, true_item in enumerate(doc_true_json["output"]["main_text"]):
        if "text" in true_item:

            pred_item = doc_pred_json["output"]["main_text"][l]

            assert "text" in pred_item, f"`text` is in {pred_item}"
            assert true_item["text"] == pred_item["text"]


def verify_tables(doc_pred_json, doc_true_json):

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


def verify_json(doc_pred_json, doc_true_json):

    if doc_pred_json.keys() != doc_true_json.keys():
        return False

    if doc_pred_json["output"].keys() != doc_true_json["output"].keys():
        return False

    assert verify_maintext(
        doc_pred_json, doc_true_json
    ), "verify_maintext(doc_pred_json, doc_true_json)"

    assert verify_tables(
        doc_pred_json, doc_true_json
    ), "verify_tables(doc_pred_json, doc_true_json)"

    return True


def verify_md(doc_pred_md, doc_true_md):
    return doc_pred_md == doc_true_md


def test_e2e_conversions():

    pdf_paths = get_pdf_paths()

    converter = get_converter()

    for path in pdf_paths:

        print(f"converting {path}")

        doc_pred_json = None
        doc_true_json = None

        try:
            doc_pred_json = converter.convert_single(path)
        except:
            continue

        doc_pred_md = doc_pred_json.render_as_markdown()

        json_path = path.with_suffix(".json")
        md_path = path.with_suffix(".md")

        if GENERATE:

            with open(json_path, "w") as fw:
                _ = doc_pred_json.model_dump()
                _ = convert_paths(_)
                fw.write(json.dumps(_, indent=2))

            with open(md_path, "w") as fw:
                fw.write(doc_pred_md)

        else:

            with open(json_path, "r") as fr:
                doc_true_json = json.load(fr)

            with open(md_path, "r") as fr:
                doc_true_md = "".join(fr.readlines())

            assert verify_cells(
                doc_pred_json.model_dump(), doc_true_json
            ), f"verify_cells(doc_pred_json, doc_true_json) for {path}"

            # assert verify_json(
            #     doc_pred_json.model_dump(), doc_true_json
            # ), f"failed json prediction for {path}"

            assert verify_md(
                doc_pred_md, doc_true_md
            ), f"failed md prediction for {path}"
