from io import BytesIO
from pathlib import Path

from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.base_models import DocumentStream, InputFormat
from docling.datamodel.document import InputDocument, _DocumentConversionInput
from docling.datamodel.settings import DocumentLimits


def test_in_doc_from_valid_path():

    test_doc_path = Path("./tests/data/pdf/2206.01062.pdf")
    doc = _make_input_doc(test_doc_path)
    assert doc.valid == True


def test_in_doc_from_invalid_path():
    test_doc_path = Path("./tests/does/not/exist.pdf")

    doc = _make_input_doc(test_doc_path)

    assert doc.valid == False


def test_in_doc_from_valid_buf():

    buf = BytesIO(Path("./tests/data/pdf/2206.01062.pdf").open("rb").read())
    stream = DocumentStream(name="my_doc.pdf", stream=buf)

    doc = _make_input_doc_from_stream(stream)
    assert doc.valid == True


def test_in_doc_from_invalid_buf():

    buf = BytesIO(b"")
    stream = DocumentStream(name="my_doc.pdf", stream=buf)

    doc = _make_input_doc_from_stream(stream)
    assert doc.valid == False


def test_in_doc_with_page_range():
    test_doc_path = Path("./tests/data/pdf/2206.01062.pdf")
    limits = DocumentLimits()
    limits.page_range = (1, 10)

    doc = InputDocument(
        path_or_stream=test_doc_path,
        format=InputFormat.PDF,
        backend=PyPdfiumDocumentBackend,
        limits=limits,
    )
    assert doc.valid == True

    limits.page_range = (9, 9)

    doc = InputDocument(
        path_or_stream=test_doc_path,
        format=InputFormat.PDF,
        backend=PyPdfiumDocumentBackend,
        limits=limits,
    )
    assert doc.valid == True

    limits.page_range = (11, 12)

    doc = InputDocument(
        path_or_stream=test_doc_path,
        format=InputFormat.PDF,
        backend=PyPdfiumDocumentBackend,
        limits=limits,
    )
    assert doc.valid == False


def test_guess_format(tmp_path):
    """Test docling.datamodel.document._DocumentConversionInput.__guess_format"""
    dci = _DocumentConversionInput(path_or_stream_iterator=[])
    temp_dir = tmp_path / "test_guess_format"
    temp_dir.mkdir()

    # Valid PDF
    buf = BytesIO(Path("./tests/data/pdf/2206.01062.pdf").open("rb").read())
    stream = DocumentStream(name="my_doc.pdf", stream=buf)
    assert dci._guess_format(stream) == InputFormat.PDF
    doc_path = Path("./tests/data/pdf/2206.01062.pdf")
    assert dci._guess_format(doc_path) == InputFormat.PDF

    # Valid MS Office
    buf = BytesIO(Path("./tests/data/docx/lorem_ipsum.docx").open("rb").read())
    stream = DocumentStream(name="lorem_ipsum.docx", stream=buf)
    assert dci._guess_format(stream) == InputFormat.DOCX
    doc_path = Path("./tests/data/docx/lorem_ipsum.docx")
    assert dci._guess_format(doc_path) == InputFormat.DOCX

    # Valid HTML
    buf = BytesIO(Path("./tests/data/html/wiki_duck.html").open("rb").read())
    stream = DocumentStream(name="wiki_duck.html", stream=buf)
    assert dci._guess_format(stream) == InputFormat.HTML
    doc_path = Path("./tests/data/html/wiki_duck.html")
    assert dci._guess_format(doc_path) == InputFormat.HTML

    # Valid MD
    buf = BytesIO(Path("./tests/data/md/wiki.md").open("rb").read())
    stream = DocumentStream(name="wiki.md", stream=buf)
    assert dci._guess_format(stream) == InputFormat.MD
    doc_path = Path("./tests/data/md/wiki.md")
    assert dci._guess_format(doc_path) == InputFormat.MD

    # Valid CSV
    buf = BytesIO(Path("./tests/data/csv/csv-comma.csv").open("rb").read())
    stream = DocumentStream(name="csv-comma.csv", stream=buf)
    assert dci._guess_format(stream) == InputFormat.CSV
    stream = DocumentStream(name="test-comma", stream=buf)
    assert dci._guess_format(stream) == InputFormat.CSV
    doc_path = Path("./tests/data/csv/csv-comma.csv")
    assert dci._guess_format(doc_path) == InputFormat.CSV

    # Valid XML USPTO patent
    buf = BytesIO(Path("./tests/data/uspto/ipa20110039701.xml").open("rb").read())
    stream = DocumentStream(name="ipa20110039701.xml", stream=buf)
    assert dci._guess_format(stream) == InputFormat.XML_USPTO
    doc_path = Path("./tests/data/uspto/ipa20110039701.xml")
    assert dci._guess_format(doc_path) == InputFormat.XML_USPTO

    buf = BytesIO(Path("./tests/data/uspto/pftaps057006474.txt").open("rb").read())
    stream = DocumentStream(name="pftaps057006474.txt", stream=buf)
    assert dci._guess_format(stream) == InputFormat.XML_USPTO
    doc_path = Path("./tests/data/uspto/pftaps057006474.txt")
    assert dci._guess_format(doc_path) == InputFormat.XML_USPTO

    # Valid XML JATS
    buf = BytesIO(Path("./tests/data/jats/elife-56337.xml").open("rb").read())
    stream = DocumentStream(name="elife-56337.xml", stream=buf)
    assert dci._guess_format(stream) == InputFormat.XML_JATS
    doc_path = Path("./tests/data/jats/elife-56337.xml")
    assert dci._guess_format(doc_path) == InputFormat.XML_JATS

    buf = BytesIO(Path("./tests/data/jats/elife-56337.nxml").open("rb").read())
    stream = DocumentStream(name="elife-56337.nxml", stream=buf)
    assert dci._guess_format(stream) == InputFormat.XML_JATS
    doc_path = Path("./tests/data/jats/elife-56337.nxml")
    assert dci._guess_format(doc_path) == InputFormat.XML_JATS

    buf = BytesIO(Path("./tests/data/jats/elife-56337.txt").open("rb").read())
    stream = DocumentStream(name="elife-56337.txt", stream=buf)
    assert dci._guess_format(stream) == InputFormat.XML_JATS
    doc_path = Path("./tests/data/jats/elife-56337.txt")
    assert dci._guess_format(doc_path) == InputFormat.XML_JATS

    # Valid XML, non-supported flavor
    xml_content = (
        '<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE docling_test SYSTEM '
        '"test.dtd"><docling>Docling parses documents</docling>'
    )
    doc_path = temp_dir / "docling_test.xml"
    doc_path.write_text(xml_content, encoding="utf-8")
    assert dci._guess_format(doc_path) == None
    buf = BytesIO(Path(doc_path).open("rb").read())
    stream = DocumentStream(name="docling_test.xml", stream=buf)
    assert dci._guess_format(stream) == None

    # Invalid USPTO patent (as plain text)
    stream = DocumentStream(name="pftaps057006474.txt", stream=BytesIO(b"xyz"))
    assert dci._guess_format(stream) == None
    doc_path = temp_dir / "pftaps_wrong.txt"
    doc_path.write_text("xyz", encoding="utf-8")
    assert dci._guess_format(doc_path) == None

    # Valid Docling JSON
    test_str = '{"name": ""}'
    stream = DocumentStream(name="test.json", stream=BytesIO(f"{test_str}".encode()))
    assert dci._guess_format(stream) == InputFormat.JSON_DOCLING
    doc_path = temp_dir / "test.json"
    doc_path.write_text(test_str, encoding="utf-8")
    assert dci._guess_format(doc_path) == InputFormat.JSON_DOCLING

    # Non-Docling JSON
    # TODO: Docling JSON is currently the single supported JSON flavor and the pipeline
    # will try to validate *any* JSON (based on suffix/MIME) as Docling JSON; proper
    # disambiguation seen as part of https://github.com/DS4SD/docling/issues/802
    test_str = "{}"
    stream = DocumentStream(name="test.json", stream=BytesIO(f"{test_str}".encode()))
    assert dci._guess_format(stream) == InputFormat.JSON_DOCLING
    doc_path = temp_dir / "test.json"
    doc_path.write_text(test_str, encoding="utf-8")
    assert dci._guess_format(doc_path) == InputFormat.JSON_DOCLING


def _make_input_doc(path):
    in_doc = InputDocument(
        path_or_stream=path,
        format=InputFormat.PDF,
        backend=PyPdfiumDocumentBackend,
    )
    return in_doc


def _make_input_doc_from_stream(doc_stream):
    in_doc = InputDocument(
        path_or_stream=doc_stream.stream,
        format=InputFormat.PDF,
        filename=doc_stream.name,
        backend=PyPdfiumDocumentBackend,
    )
    return in_doc
