<p align="center">
  <a href="https://github.com/ds4sd/docling">
    <img loading="lazy" alt="Docling" src="https://github.com/DS4SD/docling/raw/main/docs/assets/docling_processing.png" width="100%"/>
  </a>
</p>

# Docling

[![arXiv](https://img.shields.io/badge/arXiv-2408.09869-b31b1b.svg)](https://arxiv.org/abs/2408.09869)
[![Docs](https://img.shields.io/badge/docs-live-brightgreen)](https://ds4sd.github.io/docling/)
[![PyPI version](https://img.shields.io/pypi/v/docling)](https://pypi.org/project/docling/)
![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)
[![Poetry](https://img.shields.io/endpoint?url=https://python-poetry.org/badge/v0.json)](https://python-poetry.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![Pydantic v2](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/pydantic/pydantic/main/docs/badge/v2.json)](https://pydantic.dev)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![License MIT](https://img.shields.io/github/license/DS4SD/docling)](https://opensource.org/licenses/MIT)

Docling parses documents and exports them to the desired format with ease and speed.


## Features

* 🗂️ Multi-format support for input (PDF, DOCX etc.) & output (Markdown, JSON etc.)
* 📑 Advanced PDF document understanding incl. page layout, reading order & table structures
* 📝 Metadata extraction, including title, authors, references & language
* 🤖 Seamless LlamaIndex 🦙 & LangChain 🦜🔗 integration for powerful RAG / QA applications
* 🔍 OCR support for scanned PDFs
* 💻 Simple and convenient CLI

Explore the [documentation](https://ds4sd.github.io/docling/) to discover plenty examples and unlock the full power of Docling!


## Installation

To use Docling, simply install `docling` from your package manager, e.g. pip:
```bash
pip install docling
```

Works on macOS, Linux and Windows environments. Both x86_64 and arm64 architectures.

More [detailed installation instructions](https://ds4sd.github.io/docling/installation/) are available in the docs.

## Getting started

To convert individual documents, use `convert()`, for example:

```python
from docling.document_converter import DocumentConverter

source = "https://arxiv.org/pdf/2408.09869"  # document per local path or URL
converter = DocumentConverter()
result = converter.convert(source)
print(result.document.export_to_markdown())  # output: "## Docling Technical Report[...]"
```


Check out [Getting started](https://ds4sd.github.io/docling/).
You will find lots of tuning options to leverage all the advanced capabilities.


## Get help and support

Please feel free to connect with us using the [discussion section](https://github.com/DS4SD/docling/discussions).


## Technical report

For more details on Docling's inner workings, check out the [Docling Technical Report](https://arxiv.org/abs/2408.09869).

## Contributing

Please read [Contributing to Docling](https://github.com/DS4SD/docling/blob/main/CONTRIBUTING.md) for details.


## References

If you use Docling in your projects, please consider citing the following:

```bib
@techreport{Docling,
  author = {Deep Search Team},
  month = {8},
  title = {Docling Technical Report},
  url = {https://arxiv.org/abs/2408.09869},
  eprint = {2408.09869},
  doi = {10.48550/arXiv.2408.09869},
  version = {1.0.0},
  year = {2024}
}
```

## License

The Docling codebase is under MIT license. 
For individual model usage, please refer to the model licenses found in the original packages.
