from docling.document_converter import DocumentConverter

source = "https://arxiv.org/pdf/2408.09869"  # PDF path or URL
converter = DocumentConverter()
result = converter.convert_single(source)
print(result.output.export_to_markdown())  # output: ## Docling Technical Report [...]"
# if the legacy output is needed, use this version
# print(result.render_as_markdown_v1())  # output: ## Docling Technical Report [...]"
