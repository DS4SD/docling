## Conversion

### Convert a single document

To convert individual PDF documents, use `convert()`, for example:

```python
from docling.document_converter import DocumentConverter

source = "https://arxiv.org/pdf/2408.09869"  # PDF path or URL
converter = DocumentConverter()
result = converter.convert(source)
print(result.document.export_to_markdown())  # output: "### Docling Technical Report[...]"
```

### CLI

You can also use Docling directly from your command line to convert individual files —be it local or by URL— or whole directories.

A simple example would look like this:
```console
docling https://arxiv.org/pdf/2206.01062
```

To see all available options (export formats etc.) run `docling --help`. More details in the [CLI reference page](./cli.md).



### Advanced options

#### Adjust pipeline features

The example file [custom_convert.py](./examples/custom_convert.py) contains multiple ways
one can adjust the conversion pipeline and features.


##### Control PDF table extraction options

You can control if table structure recognition should map the recognized structure back to PDF cells (default) or use text cells from the structure prediction itself.
This can improve output quality if you find that multiple columns in extracted tables are erroneously merged into one.


```python
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions

pipeline_options = PdfPipelineOptions(do_table_structure=True)
pipeline_options.table_structure_options.do_cell_matching = False  # uses text cells predicted from table structure model

doc_converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
    }
)
```

Since docling 1.16.0: You can control which TableFormer mode you want to use. Choose between `TableFormerMode.FAST` (default) and `TableFormerMode.ACCURATE` (better, but slower) to receive better quality with difficult table structures.

```python
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode

pipeline_options = PdfPipelineOptions(do_table_structure=True)
pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE  # use more accurate TableFormer model

doc_converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
    }
)
```

##### Provide specific artifacts path

By default, artifacts such as models are downloaded automatically upon first usage. If you would prefer to use a local path where the artifacts have been explicitly prefetched, you can do that as follows:

```python
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline

# # to explicitly prefetch:
# artifacts_path = StandardPdfPipeline.download_models_hf()

artifacts_path = "/local/path/to/artifacts"

pipeline_options = PdfPipelineOptions(artifacts_path=artifacts_path)
doc_converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
    }
)
```

#### Impose limits on the document size

You can limit the file size and number of pages which should be allowed to process per document:

```python
from pathlib import Path
from docling.document_converter import DocumentConverter

source = "https://arxiv.org/pdf/2408.09869"
converter = DocumentConverter()
result = converter.convert(source, max_num_pages=100, max_file_size=20971520)
```

#### Convert from binary PDF streams

You can convert PDFs from a binary stream instead of from the filesystem as follows:

```python
from io import BytesIO
from docling.datamodel.base_models import DocumentStream
from docling.document_converter import DocumentConverter

buf = BytesIO(your_binary_stream)
source = DocumentStream(name="my_doc.pdf", stream=buf)
converter = DocumentConverter()
result = converter.convert(source)
```

#### Limit resource usage

You can limit the CPU threads used by Docling by setting the environment variable `OMP_NUM_THREADS` accordingly. The default setting is using 4 CPU threads.


## Chunking

You can perform a hierarchy-aware chunking of a Docling document as follows:

```python
from docling.document_converter import DocumentConverter
from docling_core.transforms.chunker import HierarchicalChunker

conv_res = DocumentConverter().convert("https://arxiv.org/pdf/2206.01062")
doc = conv_res.document
chunks = list(HierarchicalChunker().chunk(doc))

print(chunks[30])
# {
#   "text": "Lately, new types of ML models for document-layout analysis have emerged [...]",
#   "meta": {
#     "doc_items": [{
#       "self_ref": "#/texts/40",
#       "label": "text",
#       "prov": [{
#         "page_no": 2,
#         "bbox": {"l": 317.06, "t": 325.81, "r": 559.18, "b": 239.97, ...},
#       }]
#     }],
#     "headings": ["2 RELATED WORK"],
#   }
# }
```
