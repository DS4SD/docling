from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.pipeline.vlm_pipeline import VlmPipeline

source = "https://arxiv.org/pdf/2408.09869"  # document per local path or URL
converter = DocumentConverter(
    doc_converter=DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_cls=VlmPipeline)}
    )
)
result = converter.convert(source)
print(result.document.export_to_markdown())
# output: ## Docling Technical Report [...]"
