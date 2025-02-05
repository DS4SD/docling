from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import EasyOcrOptions, PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

# The location of the local artifacts, e.g. from the `docling-tools models download` command
artifacts_path = Path("PATH TO MODELS")  # <-- fill me
pipeline_options = PdfPipelineOptions(artifacts_path=artifacts_path)
pipeline_options.ocr_options = EasyOcrOptions(
    download_enabled=False, model_storage_directory=str(artifacts_path / "EasyOcr")
)

doc_converter = DocumentConverter(
    format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
)

result = doc_converter.convert("FILE TO CONVERT")  # <-- fill me
print(result.document.export_to_markdown())
