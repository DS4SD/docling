from io import BytesIO
from pathlib import Path

from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.base_models import DocumentStream, InputFormat
from docling.datamodel.document import InputDocument, _DocumentConversionInput


def test_in_doc_from_valid_path():

    test_doc_path = Path("./tests/data/2206.01062.pdf")
    doc = _make_input_doc(test_doc_path)
    assert doc.valid == True


def test_in_doc_from_invalid_path():
    test_doc_path = Path("./tests/does/not/exist.pdf")

    doc = _make_input_doc(test_doc_path)

    assert doc.valid == False


def test_in_doc_from_valid_buf():

    buf = BytesIO(Path("./tests/data/2206.01062.pdf").open("rb").read())
    stream = DocumentStream(name="my_doc.pdf", stream=buf)

    doc = _make_input_doc_from_stream(stream)
    assert doc.valid == True


def test_in_doc_from_invalid_buf():

    buf = BytesIO(b"")
    stream = DocumentStream(name="my_doc.pdf", stream=buf)

    doc = _make_input_doc_from_stream(stream)
    assert doc.valid == False


def test_guess_format(tmp_path):
    """Test docling.datamodel.document._DocumentConversionInput.__guess_format"""
    dci = _DocumentConversionInput(path_or_stream_iterator=[])
    temp_dir = tmp_path / "test_guess_format"
    temp_dir.mkdir()

    # Valid PDF
    buf = BytesIO(Path("./tests/data/2206.01062.pdf").open("rb").read())
    stream = DocumentStream(name="my_doc.pdf", stream=buf)
    assert dci._guess_format(stream) == InputFormat.PDF
    doc_path = Path("./tests/data/2206.01062.pdf")
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

    # Valid XML PubMed
    buf = BytesIO(Path("./tests/data/pubmed/elife-56337.xml").open("rb").read())
    stream = DocumentStream(name="elife-56337.xml", stream=buf)
    assert dci._guess_format(stream) == InputFormat.XML_PUBMED
    doc_path = Path("./tests/data/pubmed/elife-56337.xml")
    assert dci._guess_format(doc_path) == InputFormat.XML_PUBMED

    buf = BytesIO(Path("./tests/data/pubmed/elife-56337.nxml").open("rb").read())
    stream = DocumentStream(name="elife-56337.nxml", stream=buf)
    assert dci._guess_format(stream) == InputFormat.XML_PUBMED
    doc_path = Path("./tests/data/pubmed/elife-56337.nxml")
    assert dci._guess_format(doc_path) == InputFormat.XML_PUBMED

    buf = BytesIO(Path("./tests/data/pubmed/elife-56337.txt").open("rb").read())
    stream = DocumentStream(name="elife-56337.txt", stream=buf)
    assert dci._guess_format(stream) == InputFormat.XML_PUBMED
    doc_path = Path("./tests/data/pubmed/elife-56337.txt")
    assert dci._guess_format(doc_path) == InputFormat.XML_PUBMED

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
