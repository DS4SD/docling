import json
import logging
from pathlib import Path

import yaml

from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter

logging.basicConfig(level=logging.DEBUG)

def main():
    # Convert CSV to Docling document:
    source = "https://drive.google.com/uc?id=1zO8ekHWx9U7mrbx_0Hoxxu6od7uxJqWw&export=download"
    converter = DocumentConverter()
    result = converter.convert(source)

    # Export Docling document:
    out_path = Path("scratch")
    print(f"Document converted." f"\nSaving output to: {str(out_path)}")
    with (out_path / f"customers-100.md").open("w") as fp:
        fp.write(result.document.export_to_markdown())

    with (out_path / f"customers-100.json").open("w") as fp:
        fp.write(json.dumps(result.document.export_to_dict()))

    with (out_path / f"customers-100.yaml").open("w") as fp:
        fp.write(yaml.safe_dump(result.document.export_to_dict()))


if __name__ == "__main__":
    main()
