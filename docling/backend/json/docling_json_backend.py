from io import BytesIO
from pathlib import Path
from typing import Union

from docling_core.types.doc import DoclingDocument
from typing_extensions import override

from docling.backend.abstract_backend import DeclarativeDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import InputDocument


class DoclingJSONBackend(DeclarativeDocumentBackend):
    @override
    def __init__(
        self, in_doc: InputDocument, path_or_stream: Union[BytesIO, Path]
    ) -> None:
        super().__init__(in_doc, path_or_stream)
        self._my_in_doc = in_doc

    @override
    def is_valid(self) -> bool:
        return True

    @classmethod
    @override
    def supports_pagination(cls) -> bool:
        return False

    @classmethod
    @override
    def supported_formats(cls) -> set[InputFormat]:
        return {InputFormat.JSON_DOCLING}

    @override
    def convert(self) -> DoclingDocument:
        json_data: Union[str, bytes]
        if isinstance(self.path_or_stream, Path):
            with open(self.path_or_stream, encoding="utf-8") as f:
                json_data = f.read()
        elif isinstance(self.path_or_stream, BytesIO):
            json_data = self.path_or_stream.getvalue()
        else:
            raise RuntimeError(f"Unexpected: {type(self.path_or_stream)=}")
        doc = DoclingDocument.model_validate_json(json_data=json_data)
        return doc
