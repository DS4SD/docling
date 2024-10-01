from docling.pdf_document_converter import PdfDocumentConverter

source = "https://arxiv.org/pdf/2408.09869"  # PDF path or URL
converter = PdfDocumentConverter()
doc = converter.convert_single(source)
print(doc.render_as_markdown())  # output: ## Docling Technical Report [...]"
