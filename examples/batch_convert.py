import json
import logging
import time
from pathlib import Path
from typing import Iterable

from docling.datamodel.base_models import ConversionStatus, PipelineOptions
from docling.datamodel.document import ConversionResult, DocumentConversionInput
from docling.document_converter import DocumentConverter

_log = logging.getLogger(__name__)


def export_documents(
    conv_results: Iterable[ConversionResult],
    output_dir: Path,
):
    output_dir.mkdir(parents=True, exist_ok=True)

    success_count = 0
    failure_count = 0
    partial_success_count = 0

    for conv_res in conv_results:
        if conv_res.status == ConversionStatus.SUCCESS:
            success_count += 1
            doc_filename = conv_res.input.file.stem

            # Export Deep Search document JSON format:
            with (output_dir / f"{doc_filename}.json").open("w") as fp:
                fp.write(json.dumps(conv_res.render_as_dict()))

            # Export Text format:
            with (output_dir / f"{doc_filename}.txt").open("w") as fp:
                fp.write(conv_res.render_as_text())

            # Export Markdown format:
            with (output_dir / f"{doc_filename}.md").open("w") as fp:
                fp.write(conv_res.render_as_markdown())

            # Export Document Tags format:
            with (output_dir / f"{doc_filename}.doctags").open("w") as fp:
                fp.write(conv_res.render_as_doctags())

        elif conv_res.status == ConversionStatus.PARTIAL_SUCCESS:
            _log.info(
                f"Document {conv_res.input.file} was partially converted with the following errors:"
            )
            for item in conv_res.errors:
                _log.info(f"\t{item.error_message}")
            partial_success_count += 1
        else:
            _log.info(f"Document {conv_res.input.file} failed to convert.")
            failure_count += 1

    _log.info(
        f"Processed {success_count + partial_success_count + failure_count} docs, "
        f"of which {failure_count} failed "
        f"and {partial_success_count} were partially converted."
    )
    return success_count, partial_success_count, failure_count


def main():
    logging.basicConfig(level=logging.INFO)

    input_doc_paths = [
        Path("./tests/data/2206.01062.pdf"),
        Path("./tests/data/2203.01017v2.pdf"),
        Path("./tests/data/2305.03393v1.pdf"),
        Path("./tests/data/redp5110.pdf"),
        Path("./tests/data/redp5695.pdf"),
    ]

    # buf = BytesIO(Path("./test/data/2206.01062.pdf").open("rb").read())
    # docs = [DocumentStream(filename="my_doc.pdf", stream=buf)]
    # input = DocumentConversionInput.from_streams(docs)

    doc_converter = DocumentConverter()

    input = DocumentConversionInput.from_paths(input_doc_paths)

    start_time = time.time()

    conv_results = doc_converter.convert(input)
    success_count, partial_success_count, failure_count = export_documents(
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
