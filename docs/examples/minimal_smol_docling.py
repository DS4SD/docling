import json
import os
import time
from pathlib import Path
from urllib.parse import urlparse

import yaml

from docling.backend.docling_parse_backend import DoclingParseDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.pipeline.vlm_pipeline import VlmPipeline

# source = "https://arxiv.org/pdf/2408.09869"  # document per local path or URL
# source = "tests/data/2305.03393v1-pg9-img.png"
# source = "tests/data/2305.03393v1-pg9.pdf"
# source = "demo_data/page.png"
# source = "demo_data/original_tables.pdf"

sources = [
    "tests/data/2305.03393v1-pg9-img.png",
    # "tests/data/2305.03393v1-pg9.pdf",
    # "demo_data/page.png",
    # "demo_data/original_tables.pdf",
]

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

out_path = Path("scratch")
out_path.mkdir(parents=True, exist_ok=True)

for source in sources:
    start_time = time.time()
    print("================================================")
    print("Processing... {}".format(source))
    print("================================================")
    print("")

    res = converter.convert(source)

    print("------------------------------------------------")
    print("MD:")
    print("------------------------------------------------")
    print("")
    print(res.document.export_to_markdown())

    with (out_path / f"{res.input.file.stem}.html").open("w") as fp:
        fp.write(res.document.export_to_html())

    with (out_path / f"{res.input.file.stem}.json").open("w") as fp:
        fp.write(json.dumps(res.document.export_to_dict()))

    with (out_path / f"{res.input.file.stem}.yaml").open("w") as fp:
        fp.write(yaml.safe_dump(res.document.export_to_dict()))

    pg_num = res.document.num_pages()

    print("")
    inference_time = time.time() - start_time
    print(
        f"Total document prediction time: {inference_time:.2f} seconds, pages: {pg_num}"
    )

print("================================================")
print("done!")
print("================================================")
