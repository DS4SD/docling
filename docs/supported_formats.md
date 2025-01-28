Docling can parse various documents formats into a unified representation (Docling
Document), which it can export to different formats too — check out
[Architecture](./concepts/architecture.md) for more details.

Below you can find a listing of all supported input and output formats.

## Supported input formats

| Format | Description |
|--------|-------------|
| PDF | |
| DOCX, XLSX, PPTX | Default formats in MS Office 2007+, based on Office Open XML |
| Markdown | |
| AsciiDoc | |
| HTML, XHTML | |
| PNG, JPEG, TIFF, BMP | Image formats |

Schema-specific support:

| Format | Description |
|--------|-------------|
| USPTO XML | XML format followed by [USPTO](https://www.uspto.gov/patents) patents |
| PMC XML | XML format followed by [PubMed Central®](https://pmc.ncbi.nlm.nih.gov/) articles |
| Docling JSON | JSON-serialized [Docling Document](./concepts/docling_document.md) |

## Supported output formats

| Format | Description |
|--------|-------------|
| HTML | Both image embedding and referencing are supported |
| Markdown | |
| JSON | Lossless serialization of Docling Document |
| Text | Plain text, i.e. without Markdown markers |
| Doctags | |
