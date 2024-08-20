from pathlib import Path

import pytest

from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend, PyPdfiumPageBackend
from docling.datamodel.base_models import BoundingBox


@pytest.fixture
def test_doc_path():
    return Path("./data/2206.01062.pdf")

@pytest.fixture
def test_image_doc_path():
    return Path("/Users/cau/Documents/Data/test_data/test-image.pdf")

def test_get_text_from_rect(test_doc_path):
    doc_backend = PyPdfiumDocumentBackend(test_doc_path)
    page_backend: PyPdfiumPageBackend = doc_backend.load_page(0)

    # Get the title text of the DocLayNet paper
    textpiece = page_backend.get_text_in_rect(bbox=BoundingBox(l=102,t=77,r=511,b=124))
    ref = "DocLayNet: A Large Human-Annotated Dataset for\r\nDocument-Layout Analysis"

    assert textpiece.strip() == ref

def test_crop_page_image(test_doc_path):
    doc_backend = PyPdfiumDocumentBackend(test_doc_path)
    page_backend: PyPdfiumPageBackend = doc_backend.load_page(0)

    # Crop out "Figure 1" from the DocLayNet paper
    im = page_backend.get_page_image(scale=2, cropbox=BoundingBox(l=317,t=246,r=574,b=527))
    # im.show()

def test_num_pages(test_doc_path):
    doc_backend = PyPdfiumDocumentBackend(test_doc_path)
    doc_backend.page_count() == 9

def test_get_bitmaps(test_doc_path):
    doc_backend = PyPdfiumDocumentBackend(test_doc_path)
    for i in range(doc_backend.page_count()):
        page = doc_backend.load_page(i)
        bitmaps = page.get_bitmaps()
        for b in bitmaps:
            img = page.get_page_image(cropbox=b)
            img.show()