# Docling

<p align="center">
  <img loading="lazy" alt="Docling" src="assets/docling_processing.png" width="100%" />
</p>


[![arXiv](https://img.shields.io/badge/arXiv-2408.09869-b31b1b.svg)](https://arxiv.org/abs/2408.09869)
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

* 🗂️ Reads popular document formats (PDF, DOCX, PPTX, Images, HTML, AsciiDoc, Markdown) and exports to Markdown and JSON
* 📑 Advanced PDF document understanding incl. page layout, reading order & table structures
* 🧩 Unified, expressive [DoclingDocument](./concepts/docling_document.md) representation format
* 📝 Metadata extraction, including title, authors, references & language
* 🤖 Seamless LlamaIndex 🦙 & LangChain 🦜🔗 integration for powerful RAG / QA applications
* 🔍 OCR support for scanned PDFs
* 💻 Simple and convenient CLI
