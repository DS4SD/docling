import os
import time
from pathlib import Path
from urllib.parse import urlparse

from docling.backend.docling_parse_backend import DoclingParseDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.pipeline.vlm_pipeline import VlmPipeline

# source = "https://arxiv.org/pdf/2408.09869"  # document per local path or URL
# source = "tests/data/2305.03393v1-pg9-img.png"
source = "tests/data/2305.03393v1-pg9.pdf"
# source = "demo_data/page.png"
# source = "demo_data/original_tables.pdf"

parsed = urlparse(source)
if parsed.scheme in ("http", "https"):
    out_name = os.path.basename(parsed.path)
else:
    out_name = os.path.basename(source)

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

start_time = time.time()
print("============")
print("starting...")
print("============")
print("")

result = converter.convert(source)

print("------------")
print("MD:")
print("------------")
print("")
print(result.document.export_to_markdown())

Path("scratch").mkdir(parents=True, exist_ok=True)
result.document.save_as_html(
    filename=Path("scratch/{}.html".format(out_name)),
    image_mode=ImageRefMode.REFERENCED,
    labels=[*DEFAULT_EXPORT_LABELS, DocItemLabel.FOOTNOTE],
)

pg_num = result.document.num_pages()

print("")
inference_time = time.time() - start_time
print(f"Total document prediction time: {inference_time:.2f} seconds, pages: {pg_num}")
print("============")
print("done!")
print("============")

# output: ## Docling Technical Report [...]"
