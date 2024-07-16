<p align="center">
  <a href="https://github.com/ds4sd/docling"> <img loading="lazy" alt="Docling" src="https://github.com/DS4SD/docling/raw/main/logo.png" width="150" /> </a>
</p>

# Docling

Docling bundles PDF document conversion to JSON and Markdown in an easy, self-contained package.

## Features
* ⚡ Converts any PDF document to JSON or Markdown format, stable and lightning fast
* 📑 Understands detailed page layout, reading order and recovers table structures
* 📝 Extracts metadata from the document, such as title, authors, references and language
* 🔍 Optionally applies OCR (use with scanned PDFs)

## Setup

For general usage, you can simply install `docling` through `pip` from the pypi package index.
```
pip install docling
```

**Notes**:
* Works on macOS and Linux environments. Windows platforms are currently not tested.

### Development setup

To develop for `docling`, you need Python 3.11 and `poetry`. Install poetry from [here](https://python-poetry.org/docs/#installing-with-the-official-installer).

Once you have `poetry` installed and cloned this repo, create an environment and install `docling` from the repo root:

```bash
poetry env use $(which python3.11)
poetry shell
poetry install
```

## Usage

For basic usage, see the [convert.py](https://github.com/DS4SD/docling/blob/main/examples/convert.py) example module. Run with:

```
python examples/convert.py
```
The output of the above command will be written to `./scratch`.

### Enable or disable pipeline features

You can control if table structure recognition or OCR should be performed by arguments passed to `DocumentConverter` 
```python
doc_converter = DocumentConverter(
    artifacts_path=artifacts_path,
    pipeline_options=PipelineOptions(do_table_structure=False, # Controls if table structure is recovered. 
                                     do_ocr=True), # Controls if OCR is applied (ignores programmatic content)
)
```

### Impose limits on the document size

You can limit the file size and number of pages which should be allowed to process per document.
```python
paths = [Path("./test/data/2206.01062.pdf")]

input = DocumentConversionInput.from_paths(
    paths, limits=DocumentLimits(max_num_pages=100, max_file_size=20971520)
)
```

### Convert from binary PDF streams 

You can convert PDFs from a binary stream instead of from the filesystem as follows:
```python
buf = BytesIO(your_binary_stream)
docs = [DocumentStream(filename="my_doc.pdf", stream=buf)]
input = DocumentConversionInput.from_streams(docs)
converted_docs = doc_converter.convert(input)
```
### Limit resource usage

You can limit the CPU threads used by `docling` by setting the environment variable `OMP_NUM_THREADS` accordingly. The default setting is using 4 CPU threads.


## Contributing

Please read [Contributing to Docling](https://github.com/DS4SD/docling/blob/main/CONTRIBUTING.md) for details.


## References

If you use `Docling` in your projects, please consider citing the following:

```bib
@software{Docling,
author = {Deep Search Team},
month = {7},
title = {{Docling}},
url = {https://github.com/DS4SD/docling},
version = {main},
year = {2024}
}
```

## License

The `Docling` codebase is under MIT license.
For individual model usage, please refer to the model licenses found in the original packages.
