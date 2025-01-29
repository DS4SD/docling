Docling is available as an official [LlamaIndex](https://docs.llamaindex.ai/) extension.

To get started, check out the [step-by-step guide in LlamaIndex](https://docs.llamaindex.ai/en/stable/examples/data_connectors/DoclingReaderDemo/).

## Components

### Docling Reader

Reads document files and uses Docling to populate LlamaIndex `Document` objects — either serializing Docling's data model (losslessly, e.g. as JSON) or exporting to a simplified format (lossily, e.g. as Markdown).

- 💻 [Docling Reader GitHub](https://github.com/run-llama/llama_index/tree/main/llama-index-integrations/readers/llama-index-readers-docling)
- 📖 [Docling Reader docs](https://docs.llamaindex.ai/en/stable/api_reference/readers/docling/)
- 📦 [Docling Reader PyPI](https://pypi.org/project/llama-index-readers-docling/)

### Docling Node Parser

Reads LlamaIndex `Document` objects populated in Docling's format by Docling Reader and, using its knowledge of the Docling format, parses them to LlamaIndex `Node` objects for downstream usage in LlamaIndex applications, e.g. as chunks for embedding.

- 💻 [Docling Node Parser GitHub](https://github.com/run-llama/llama_index/tree/main/llama-index-integrations/node_parser/llama-index-node-parser-docling)
- 📖 [Docling Node Parser docs](https://docs.llamaindex.ai/en/stable/api_reference/node_parser/docling/)
- 📦 [Docling Node Parser PyPI](https://pypi.org/project/llama-index-node-parser-docling/)
