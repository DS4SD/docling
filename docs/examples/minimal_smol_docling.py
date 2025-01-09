from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.pipeline.vlm_pipeline import VlmPipeline

# source = "https://arxiv.org/pdf/2408.09869"  # document per local path or URL
source = "tests/data/2305.03393v1-pg9-img.png"

pipeline_options = PdfPipelineOptions()
pipeline_options.artifacts_path = "model_artifacts"

converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(
            pipeline_cls=VlmPipeline, pipeline_options=pipeline_options
        )
    }
)
result = converter.convert(source)
print(result.document.export_to_markdown())

print("done!")

# output: ## Docling Technical Report [...]"
