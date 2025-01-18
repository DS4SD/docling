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

To see all available options (export formats etc.) run `docling --help`. More details in the [CLI reference page](./reference/cli.md).

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

You can chunk a Docling document using a [chunker](concepts/chunking.md), such as a
`HybridChunker`, as shown below (for more details check out
[this example](examples/hybrid_chunking.ipynb)):

```python
from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker

conv_res = DocumentConverter().convert("https://arxiv.org/pdf/2206.01062")
doc = conv_res.document

chunker = HybridChunker(tokenizer="BAAI/bge-small-en-v1.5")  # set tokenizer as needed
chunk_iter = chunker.chunk(doc)
```

An example chunk would look like this:

```python
print(list(chunk_iter)[11])
# {
#   "text": "In this paper, we present the DocLayNet dataset. [...]",
#   "meta": {
#     "doc_items": [{
#       "self_ref": "#/texts/28",
#       "label": "text",
#       "prov": [{
#         "page_no": 2,
#         "bbox": {"l": 53.29, "t": 287.14, "r": 295.56, "b": 212.37, ...},
#       }], ...,
#     }, ...],
#     "headings": ["1 INTRODUCTION"],
#   }
# }
```

## Plugins

Docling supports plugins that can modify documents during preprocessing (before conversion) and conversion results during postprocessing (after conversion). Plugins can be used to add custom metadata, modify text content, or implement custom processing logic.

### Creating custom plugins

Create custom plugins by subclassing `DoclingPlugin` and implementing `preprocess` and/or `postprocess` methods:

```python
from docling.plugins import DoclingPlugin, PluginMetadata
from docling.datamodel.document import InputDocument, ConversionResult

class MyCustomPlugin(DoclingPlugin):
    def __init__(self):
        super().__init__(
            name="MyCustomPlugin", # Must contain only letters, numbers, underscores, or hyphens
            metadata=PluginMetadata(
                version="0.1.0", # Must adhere to semantic versioning
                description="A custom plugin example",
                author="Your Name",
                preprocess={},
                postprocess={}
            )
        )
    
    def preprocess(self, input_doc: InputDocument) -> InputDocument:
        # Modify input document before conversion
        return input_doc
    
    def postprocess(self, result: ConversionResult) -> ConversionResult:
        # Modify conversion result after conversion
        return result
```

### Using plugins in Python

To use plugins with Docling, create a plugin instance and pass it to the DocumentConverter:

```python
from docling.document_converter import DocumentConverter
from docling.plugins import DoclingPlugin, PluginMetadata

# Create plugin instance
my_custom_plugin = MyCustomPlugin()

# Initialize converter with plugins
converter = DocumentConverter(plugins=[my_custom_plugin])

# Convert as usual
result = converter.convert("path/to/document.pdf")
```

Enriched plugin metadata are accessible through the `plugins` attribute of the conversion result:

```python
result = converter.convert("path/to/document.pdf")
plugin_metadata = result.plugins["MyCustomPlugin"]
```

Since plugins transform the document and conversion result, you can access the modified document and results through the `result` object just like you would without plugins. For example:

```python
print(result.document.texts[0].text)
```

For a complete example of plugin implementation, see [plugin_basic.py](./examples/plugins/plugin_basic.py).

### Using plugins with CLI

You can use plugins through the CLI by specifying the module path and plugin class using the `--plugin` (or `-p`) option:

```console
docling input.pdf --plugin "myapp.plugins:MyCustomPlugin"
```

Multiple plugins can be used by repeating the option:

```console
docling input.pdf -p "myapp.plugins:FirstPlugin" -p "other.module:SecondPlugin"
```

The plugin specification must be in the format `module.path:PluginClass`. For example:
- `myapp.plugins:MyCustomPlugin` - loads the MyCustomPlugin class from myapp.plugins module
- `docling.plugins.examples:BasicPlugin` - loads the BasicPlugin from docling.plugins.examples

Note: The specified plugin module must be importable from your Python environment (i.e., installed or in the Python path).
