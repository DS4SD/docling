import json
from pathlib import Path
from typing import List

import pytest
from deepsearch_glm.andromeda_nlp import nlp_model  # type: ignore
from docling_core.types.doc import DocItemLabel
from docling_core.utils.legacy import (
    doc_item_label_to_legacy_name,
    docling_document_to_legacy,
)

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.utils.glm_utils import to_docling_document


@pytest.fixture
def test_glm_paths():
    return [
        Path("tests/data/utils/01030000000016.json"),
    ]


def generate_glm_docs(test_glm_paths: List[Path]):
    r"""
    Call this method only to generate the test dataset.
    No need to call this method during the regular testing.

    Run NLP model and convert PDF into GLM documents
    """
    # Initialize the NLP model
    model = nlp_model(loglevel="error", text_ordering=True)

    # Create the document converter
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = False

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )
    pdf_paths = [p.with_suffix(".pdf") for p in test_glm_paths]
    res = converter.convert_all(pdf_paths, raises_on_error=True)

    # convert pdf -> DoclingDocument -> legacy -> glm_doc
    for glm_path, conv_res in zip(test_glm_paths, res):
        doc = conv_res.document
        legacy_doc = docling_document_to_legacy(doc)
        legacy_doc_dict = legacy_doc.model_dump(by_alias=True, exclude_none=True)
        glm_doc = model.apply_on_doc(legacy_doc_dict)

        # Save the glm doc
        with open(glm_path, "w") as fd:
            json.dump(glm_doc, fd)


def test_convert_glm_to_docling(test_glm_paths):
    name_mapping = {doc_item_label_to_legacy_name(v): v.value for v in DocItemLabel}

    for glm_path in test_glm_paths:
        with open(glm_path, "r") as fd:
            glm_doc = json.load(fd)

        # Map the page_element.name of GLM into the label of docling
        for page_element in glm_doc["page-elements"]:
            pname = page_element["name"]
            if pname in name_mapping:
                page_element["name"] = name_mapping[pname]

        doc = to_docling_document(glm_doc)
        print(doc)


if __name__ == "__main__":
    # generate_glm_docs([
    #     Path("tests/data/utils/01030000000016.json"),
    # ])

    test_convert_glm_to_docling(
        [
            Path("tests/data/utils/01030000000016.json"),
        ]
    )
