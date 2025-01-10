from pathlib import Path

from docling.backend.docling_parse_backend import DoclingParseDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.pipeline.vlm_pipeline import VlmPipeline

# source = "https://arxiv.org/pdf/2408.09869"  # document per local path or URL
# source = "tests/data/2305.03393v1-pg9-img.png"
source = "tests/data/2305.03393v1-pg9.pdf"
# source = "page.png"

pipeline_options = PdfPipelineOptions()
pipeline_options.generate_page_images = True
pipeline_options.artifacts_path = "model_artifacts"

from docling_core.types.doc import DocItemLabel, ImageRefMode
from docling_core.types.doc.document import DEFAULT_EXPORT_LABELS

converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(
            pipeline_cls=VlmPipeline,
            pipeline_options=pipeline_options,
        ),
        InputFormat.IMAGE: PdfFormatOption(
            pipeline_cls=VlmPipeline,
            pipeline_options=pipeline_options,
        ),
    }
)

print("============")
print("starting...")
print("============")
print("")

result = converter.convert(source)

# print("------------")
# print("result:")
# print("------------")
# print("")
# print(result)

print("------------")
print("MD:")
print("------------")
print("")
print(result.document.export_to_markdown())

Path("scratch").mkdir(parents=True, exist_ok=True)
result.document.save_as_html(
    filename=Path("scratch/smol_export.html"),
    image_mode=ImageRefMode.REFERENCED,
    labels=[*DEFAULT_EXPORT_LABELS, DocItemLabel.FOOTNOTE],
)

print("")
print("============")
print("done!")
print("============")

# output: ## Docling Technical Report [...]"
