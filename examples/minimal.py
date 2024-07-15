from docling.datamodel.document import DocumentConversionInput
from docling.document_converter import DocumentConverter

artifacts_path = DocumentConverter.download_models_hf()
doc_converter = DocumentConverter(artifacts_path=artifacts_path)

input = DocumentConversionInput.from_paths(["factsheet.pdf"])
converted_docs = doc_converter.convert(input)

for d in converted_docs:
    print(d.render_as_dict())
