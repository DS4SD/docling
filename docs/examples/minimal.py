from docling.document_converter import DocumentConverter

source = "https://arxiv.org/pdf/2408.09869"  # PDF path or URL
converter = DocumentConverter()
result = converter.convert(source)
print(
    result.document.export_to_markdown()
)  # output: ## Docling Technical Report [...]"
# if the legacy output is needed, use this version
# print(result.legacy_document.export_to_markdown())  # output: ## Docling Technical Report [...]"
