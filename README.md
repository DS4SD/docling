## Additional Features: 
- Integrated PaddleOCR - For improved OCR capabilities.

To know more about the original repository refer to the readme and documentation available at: </br>
[Docling Github Repo](https://github.com/DS4SD/docling)
[Docling Documentation](https://ds4sd.github.io/docling/)

## PaddleOCR Usage - Demo:
```python
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, ImageFormatOption, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode, TableStructureOptions

pipeline_options = PdfPipelineOptions(do_table_structure=True, generate_page_images=True, images_scale=2.0)
pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE  # use more accurate TableFormer model
pipeline_options.table_structure_options = TableStructureOptions(do_cell_matching=True)
pipeline_options.ocr_options = PaddleOcrOptions(lang="en")

doc_converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
        InputFormat.IMAGE: ImageFormatOption(pipeline_options=pipeline_options)
    }
)
result = doc_converter.convert("sample_file.pdf")
print(result.document.export_to_markdown())

```
## License

The Docling codebase is under MIT license.
For individual model usage, please refer to the model licenses found in the original packages.

## IBM ❤️ Open Source AI

Docling has been brought to you by IBM.
