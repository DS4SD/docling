<p align="center">
  <a href="https://github.com/ds4sd/docling">
    <img loading="lazy" alt="Docling" src="https://github.com/DS4SD/docling/raw/main/logo.png" width="150" />
  </a>
</p>

# Docling

[![arXiv](https://img.shields.io/badge/arXiv-2408.09869-b31b1b.svg)](https://arxiv.org/abs/2408.09869)
[![PyPI version](https://img.shields.io/pypi/v/docling)](https://pypi.org/project/docling/)
![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)
[![Poetry](https://img.shields.io/endpoint?url=https://python-poetry.org/badge/v0.json)](https://python-poetry.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![Pydantic v2](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/pydantic/pydantic/main/docs/badge/v2.json)](https://pydantic.dev)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![License MIT](https://img.shields.io/github/license/DS4SD/docling)](https://opensource.org/licenses/MIT)

Docling bundles PDF document conversion to JSON and Markdown in an easy, self-contained package.

## Features
* ⚡ Converts any PDF document to JSON or Markdown format, stable and lightning fast
* 📑 Understands detailed page layout, reading order and recovers table structures
* 📝 Extracts metadata from the document, such as title, authors, references and language
* 🔍 Includes OCR support for scanned PDFs
* 🤖 Integrates easily with LLM app / RAG frameworks like 🦙 LlamaIndex and 🦜🔗 LangChain
* 💻 Provides a simple and convenient CLI

## Installation

To use Docling, simply install `docling` from your package manager, e.g. pip:
```bash
pip install docling
```

> [!NOTE]
> Works on macOS and Linux environments. Windows platforms are currently not tested.

<details>
  <summary><b>Alternative PyTorch distributions</b></summary>

  The Docling models depend on the [PyTorch](https://pytorch.org/) library.
  Depending on your architecture, you might want to use a different distribution of `torch`.
  For example, you might want support for different accelerator or for a cpu-only version.
  All the different ways for installing `torch` are listed on their website <https://pytorch.org/>.

  One common situation is the installation on Linux systems with cpu-only support.
  In this case, we suggest the installation of Docling with the following options

  ```bash
  # Example for installing on the Linux cpu-only version
  pip install docling --extra-index-url https://download.pytorch.org/whl/cpu
  ```
</details>

<details>
  <summary><b>Docling development setup</b></summary>

  To develop for Docling (features, bugfixes etc.), install as follows from your local clone's root dir:
  ```bash
  poetry install --all-extras
  ```
</details>

## Getting started

### Convert a single document

To convert invidual PDF documents, use `convert_single()`, for example:
```python
from docling.document_converter import DocumentConverter

source = "https://arxiv.org/pdf/2408.09869"  # PDF path or URL
converter = DocumentConverter()
result = converter.convert_single(source)
print(result.render_as_markdown())  # output: "## Docling Technical Report[...]"
print(result.render_as_doctags())  # output: "<document><title><page_1><loc_20>..."
```

### Convert a batch of documents

For an example of batch-converting documents, see [batch_convert.py](https://github.com/DS4SD/docling/blob/main/examples/batch_convert.py).

From a local repo clone, you can run it with:

```
python examples/batch_convert.py
```
The output of the above command will be written to `./scratch`.

### CLI

You can also use Docling directly from your command line to convert individual files —be it local or by URL— or whole directories.

A simple example would look like this:
```console
docling https://arxiv.org/pdf/2206.01062
```

To see all available options (export formats etc.) run `docling --help`.

<details>
  <summary><b>CLI reference</b></summary>

  Here are the available options as of this writing (for an up-to-date listing, run `docling --help`):

  ```console
  $ docling --help

  Usage: docling [OPTIONS] source

  ╭─ Arguments ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
  │ *    input_sources      source  PDF files to convert. Can be local file / directory paths or URL. [default: None] [required] │
  ╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
  ╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
  │ --json       --no-json                            If enabled the document is exported as JSON. [default: no-json]            │
  │ --md         --no-md                              If enabled the document is exported as Markdown. [default: md]             │
  │ --txt        --no-txt                             If enabled the document is exported as Text. [default: no-txt]             │
  │ --doctags    --no-doctags                         If enabled the document is exported as Doc Tags. [default: no-doctags]     │
  │ --ocr        --no-ocr                             If enabled, the bitmap content will be processed using OCR. [default: ocr] │
  │ --backend                    [pypdfium2|docling]  The PDF backend to use. [default: docling]                                 │
  │ --output                     PATH                 Output directory where results are saved. [default: .]                     │
  │ --version                                         Show version information.                                                  │
  │ --help                                            Show this message and exit.                                                │
  ╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
  ```
</details>

### RAG
Check out the following examples showcasing RAG using Docling with standard LLM application frameworks:
- [Basic RAG pipeline with 🦙 LlamaIndex](https://github.com/DS4SD/docling/tree/main/examples/rag_llamaindex.ipynb)
- [Basic RAG pipeline with 🦜🔗 LangChain](https://github.com/DS4SD/docling/tree/main/examples/rag_langchain.ipynb)

## Advanced features

### Adjust pipeline features

The example file [custom_convert.py](https://github.com/DS4SD/docling/blob/main/examples/custom_convert.py) contains multiple ways
one can adjust the conversion pipeline and features.


#### Control pipeline options

You can control if table structure recognition or OCR should be performed by arguments passed to `DocumentConverter`:
```python
doc_converter = DocumentConverter(
    artifacts_path=artifacts_path,
    pipeline_options=PipelineOptions(
        do_table_structure=False,  # controls if table structure is recovered
        do_ocr=True,  # controls if OCR is applied (ignores programmatic content)
    ),
)
```

#### Control table extraction options

You can control if table structure recognition should map the recognized structure back to PDF cells (default) or use text cells from the structure prediction itself.
This can improve output quality if you find that multiple columns in extracted tables are erroneously merged into one.


```python
pipeline_options = PipelineOptions(do_table_structure=True)
pipeline_options.table_structure_options.do_cell_matching = False  # uses text cells predicted from table structure model

doc_converter = DocumentConverter(
    artifacts_path=artifacts_path,
    pipeline_options=pipeline_options,
)
```

### Impose limits on the document size

You can limit the file size and number of pages which should be allowed to process per document:
```python
conv_input = DocumentConversionInput.from_paths(
    paths=[Path("./test/data/2206.01062.pdf")],
    limits=DocumentLimits(max_num_pages=100, max_file_size=20971520)
)
```

### Convert from binary PDF streams

You can convert PDFs from a binary stream instead of from the filesystem as follows:
```python
buf = BytesIO(your_binary_stream)
docs = [DocumentStream(filename="my_doc.pdf", stream=buf)]
conv_input = DocumentConversionInput.from_streams(docs)
results = doc_converter.convert(conv_input)
```
### Limit resource usage

You can limit the CPU threads used by Docling by setting the environment variable `OMP_NUM_THREADS` accordingly. The default setting is using 4 CPU threads.

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
