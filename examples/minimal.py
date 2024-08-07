from docling.document_converter import DocumentConverter

source = "https://arxiv.org/pdf/2206.01062"  # PDF path or URL
converter = DocumentConverter()
doc = converter.convert_single(source)
print(
    doc.export_to_markdown()
)  # output: "## DocLayNet: A Large Human-Annotated Dataset for Document-Layout Analysis [...]"
