import json
import time
from pathlib import Path

import yaml

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    VlmPipelineOptions,
    granite_vision_vlm_conversion_options,
    smoldocling_vlm_conversion_options,
)
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.pipeline.vlm_pipeline import VlmPipeline

sources = [
    # "https://arxiv.org/pdf/2408.09869",
    "tests/data/2305.03393v1-pg9-img.png",
    # "tests/data/2305.03393v1-pg9.pdf",
]

pipeline_options = VlmPipelineOptions()  # artifacts_path="~/local_model_artifacts/"
pipeline_options.generate_page_images = True
# If force_backend_text = True, text from backend will be used instead of generated text
pipeline_options.force_backend_text = False

pipeline_options.vlm_options = smoldocling_vlm_conversion_options

# Choose alternative VLM models:
# pipeline_options.vlm_options = granite_vision_vlm_conversion_options

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

    for page in res.pages:
        print("")
        print("Predicted page in DOCTAGS:")
        print(page.predictions.vlm_response.text)

    res.document.save_as_html(
        filename=Path("{}/{}.html".format(out_path, res.input.file.stem)),
        image_mode=ImageRefMode.REFERENCED,
        labels=[*DEFAULT_EXPORT_LABELS, DocItemLabel.FOOTNOTE],
    )

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
