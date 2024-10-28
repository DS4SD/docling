from pathlib import Path

from docling.backend.html_backend import HTMLDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import InputDocument, SectionHeaderItem


def test_heading_levels():
    in_path = Path("tests/data/wiki_duck.html")
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
