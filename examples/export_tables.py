import logging
import time
from pathlib import Path
from typing import Tuple

import pandas as pd

from docling.datamodel.base_models import ConversionStatus
from docling.datamodel.document import DocumentConversionInput
from docling.document_converter import DocumentConverter

_log = logging.getLogger(__name__)


def main():
    logging.basicConfig(level=logging.INFO)

    input_doc_paths = [
        Path("./tests/data/2206.01062.pdf"),
    ]
    output_dir = Path("./scratch")

    input_files = DocumentConversionInput.from_paths(input_doc_paths)

    doc_converter = DocumentConverter()

    start_time = time.time()

    conv_results = doc_converter.convert(input_files)

    success_count = 0
    failure_count = 0
    output_dir.mkdir(parents=True, exist_ok=True)
    for conv_res in conv_results:
        if conv_res.status != ConversionStatus.SUCCESS:
            _log.info(f"Document {conv_res.input.file} failed to convert.")
            failure_count += 1
            continue

        doc_filename = conv_res.input.file.stem

        # Export tables
        for table_ix, table in enumerate(conv_res.output.tables):
            table_df: pd.DataFrame = table.export_to_dataframe()
            print(f"## Table {table_ix}")
            print(table_df.to_markdown())

            # Save the table as csv
            element_csv_filename = output_dir / f"{doc_filename}-table-{table_ix+1}.csv"
            _log.info(f"Saving CSV table to {element_csv_filename}")
            table_df.to_csv(element_csv_filename)

            # Save the table as html
            element_html_filename = (
                output_dir / f"{doc_filename}-table-{table_ix+1}.html"
            )
            _log.info(f"Saving HTML table to {element_html_filename}")
            with element_html_filename.open("w") as fp:
                fp.write(table.export_to_html())

        success_count += 1

    end_time = time.time() - start_time

    _log.info(f"All documents were converted in {end_time:.2f} seconds.")

    if failure_count > 0:
        raise RuntimeError(
            f"The example failed converting {failure_count} on {len(input_doc_paths)}."
        )


if __name__ == "__main__":
    main()
