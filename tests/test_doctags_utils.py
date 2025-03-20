from PIL import Image as PILImage

from docling.utils.doctags_utils import remove_doctags_content


def test_remove_doctags_content():
    img = PILImage.open("./tests/data_scanned/ocr_test.png")
    with open("./tests/data_scanned/groundtruth/docling_v2/ocr_test.doctags.txt") as f:
        doctags = f.read()
    actual = remove_doctags_content([doctags] * 2, [img] * 2)
    expected = """<doctag><text><loc_58><loc_44><loc_426><loc_91></text>
<page_break>
<text><loc_58><loc_44><loc_426><loc_91></text>
</doctag>"""
    assert actual == expected
