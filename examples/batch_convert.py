import json
import logging
import time
from pathlib import Path
from typing import Iterable

from docling.datamodel.base_models import ConversionStatus, PipelineOptions
from docling.datamodel.document import ConvertedDocument, DocumentConversionInput
from docling.document_converter import DocumentConverter

_log = logging.getLogger(__name__)


def export_documents(
    converted_docs: Iterable[ConvertedDocument],
    output_dir: Path,
):
    output_dir.mkdir(parents=True, exist_ok=True)

    success_count = 0
    failure_count = 0
    partial_success_count = 0

    for doc in converted_docs:
        if doc.status == ConversionStatus.SUCCESS:
            success_count += 1
            doc_filename = doc.input.file.stem

            # Export Deep Search document JSON format:
            with (output_dir / f"{doc_filename}.json").open("w") as fp:
                fp.write(json.dumps(doc.render_as_dict()))

            # Export Markdown format:
            with (output_dir / f"{doc_filename}.md").open("w") as fp:
                fp.write(doc.render_as_markdown())
        elif doc.status == ConversionStatus.PARTIAL_SUCCESS:
            _log.info(
                f"Document {doc.input.file} was partially converted with the following errors:"
            )
            for item in doc.errors:
                _log.info(f"\t{item.error_message}")
            partial_success_count += 1
        else:
            _log.info(f"Document {doc.input.file} failed to convert.")
            failure_count += 1

    _log.info(
        f"Processed {success_count + partial_success_count + failure_count} docs, "
        f"of which {failure_count} failed "
        f"and {partial_success_count} were partially converted."
    )


def main():
    logging.basicConfig(level=logging.INFO)

    input_doc_paths = [
        Path("./test/data/2206.01062.pdf"),
        Path("./test/data/2203.01017v2.pdf"),
        Path("./test/data/2305.03393v1.pdf"),
        Path("./test/data/redp5110.pdf"),
        Path("./test/data/redp5695.pdf"),
    ]

    # buf = BytesIO(Path("./test/data/2206.01062.pdf").open("rb").read())
    # docs = [DocumentStream(filename="my_doc.pdf", stream=buf)]
    # input = DocumentConversionInput.from_streams(docs)

    doc_converter = DocumentConverter()

    input = DocumentConversionInput.from_paths(input_doc_paths)

    start_time = time.time()

    converted_docs = doc_converter.convert(input)
    export_documents(converted_docs, output_dir=Path("./scratch"))

    end_time = time.time() - start_time

    _log.info(f"All documents were converted in {end_time:.2f} seconds.")


if __name__ == "__main__":
    main()
