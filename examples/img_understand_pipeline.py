import logging
import os
import time
from pathlib import Path
from typing import Iterable

import httpx
from dotenv import load_dotenv

from docling.datamodel.base_models import ConversionStatus
from docling.datamodel.document import ConversionResult, DocumentConversionInput
from docling.document_converter import DocumentConverter
from docling.pipeline.img_understand_pipeline import (
    ImgUnderstandApiOptions,
    ImgUnderstandPipeline,
    ImgUnderstandPipelineOptions,
    ImgUnderstandVllmOptions,
)

_log = logging.getLogger(__name__)


def export_documents(
    conv_results: Iterable[ConversionResult],
    output_dir: Path,
):
    output_dir.mkdir(parents=True, exist_ok=True)

    success_count = 0
    failure_count = 0

    for conv_res in conv_results:
        if conv_res.status == ConversionStatus.SUCCESS:
            success_count += 1
            doc_filename = conv_res.input.file.stem

            # # Export Deep Search document JSON format:
            # with (output_dir / f"{doc_filename}.json").open("w") as fp:
            #     fp.write(json.dumps(conv_res.render_as_dict()))

            # # Export Text format:
            # with (output_dir / f"{doc_filename}.txt").open("w") as fp:
            #     fp.write(conv_res.render_as_text())

            # # Export Markdown format:
            # with (output_dir / f"{doc_filename}.md").open("w") as fp:
            #     fp.write(conv_res.render_as_markdown())

            # # Export Document Tags format:
            # with (output_dir / f"{doc_filename}.doctags").open("w") as fp:
            #     fp.write(conv_res.render_as_doctags())

        else:
            _log.info(f"Document {conv_res.input.file} failed to convert.")
            failure_count += 1

    _log.info(
        f"Processed {success_count + failure_count} docs, of which {failure_count} failed"
    )

    return success_count, failure_count


def _get_iam_access_token(api_key: str) -> str:
    res = httpx.post(
        url="https://iam.cloud.ibm.com/identity/token",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data=f"grant_type=urn:ibm:params:oauth:grant-type:apikey&apikey={api_key}",
    )
    res.raise_for_status()
    api_out = res.json()
    print(f"{api_out=}")
    return api_out["access_token"]


def main():
    logging.basicConfig(level=logging.INFO)

    input_doc_paths = [
        Path("./tests/data/2206.01062.pdf"),
    ]

    load_dotenv()
    api_key = os.environ.get("WX_API_KEY")
    project_id = os.environ.get("WX_PROJECT_ID")

    doc_converter = DocumentConverter(
        pipeline_cls=ImgUnderstandPipeline,
        # TODO: make DocumentConverter provide the correct default value
        # for pipeline_options, given the pipeline_cls
        pipeline_options=ImgUnderstandPipelineOptions(
            img_understand_options=ImgUnderstandApiOptions(
                url="https://us-south.ml.cloud.ibm.com/ml/v1/text/chat?version=2023-05-29",
                headers={
                    "Authorization": "Bearer " + _get_iam_access_token(api_key=api_key),
                },
                params=dict(
                    model_id="meta-llama/llama3-llava-next-8b-hf",
                    project_id=project_id,
                    max_tokens=512,
                    seed=42,
                ),
                llm_prompt="Describe this figure in three sentences.",
                provenance="llama3-llava-next-8b-hf",
            )
        ),
    )

    # Define input files
    input = DocumentConversionInput.from_paths(input_doc_paths)

    start_time = time.time()

    conv_results = doc_converter.convert(input)
    success_count, failure_count = export_documents(
        conv_results, output_dir=Path("./scratch")
    )

    end_time = time.time() - start_time

    _log.info(f"All documents were converted in {end_time:.2f} seconds.")

    if failure_count > 0:
        raise RuntimeError(
            f"The example failed converting {failure_count} on {len(input_doc_paths)}."
        )


if __name__ == "__main__":
    main()
