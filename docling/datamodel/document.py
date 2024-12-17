import logging
import re
from enum import Enum
from io import BytesIO
from pathlib import Path, PurePath
from typing import (
    TYPE_CHECKING,
    Dict,
    Iterable,
    List,
    Literal,
    Optional,
    Set,
    Type,
    Union,
)

import filetype
from docling_core.types.doc import (
    DocItem,
    DocItemLabel,
    DoclingDocument,
    PictureItem,
    SectionHeaderItem,
    TableItem,
    TextItem,
)
from docling_core.types.doc.document import ListItem
from docling_core.types.legacy_doc.base import (
    BaseText,
    Figure,
    GlmTableCell,
    PageDimensions,
    PageReference,
    Prov,
    Ref,
)
from docling_core.types.legacy_doc.base import Table as DsSchemaTable
from docling_core.types.legacy_doc.base import TableCell
from docling_core.types.legacy_doc.document import (
    CCSDocumentDescription as DsDocumentDescription,
)
from docling_core.types.legacy_doc.document import CCSFileInfoObject as DsFileInfoObject
from docling_core.types.legacy_doc.document import ExportedCCSDocument as DsDocument
from docling_core.utils.file import resolve_source_to_stream
from docling_core.utils.legacy import docling_document_to_legacy
from pydantic import BaseModel
from typing_extensions import deprecated

from docling.backend.abstract_backend import (
    AbstractDocumentBackend,
    PaginatedDocumentBackend,
)
from docling.datamodel.base_models import (
    AssembledUnit,
    ConversionStatus,
    DocumentStream,
    ErrorItem,
    FormatToExtensions,
    FormatToMimeType,
    InputFormat,
    MimeTypeToFormat,
    Page,
)
from docling.datamodel.settings import DocumentLimits
from docling.utils.profiling import ProfilingItem
from docling.utils.utils import create_file_hash, create_hash

if TYPE_CHECKING:
    from docling.document_converter import FormatOption

_log = logging.getLogger(__name__)

layout_label_to_ds_type = {
    DocItemLabel.TITLE: "title",
    DocItemLabel.DOCUMENT_INDEX: "table",
    DocItemLabel.SECTION_HEADER: "subtitle-level-1",
    DocItemLabel.CHECKBOX_SELECTED: "checkbox-selected",
    DocItemLabel.CHECKBOX_UNSELECTED: "checkbox-unselected",
    DocItemLabel.CAPTION: "caption",
    DocItemLabel.PAGE_HEADER: "page-header",
    DocItemLabel.PAGE_FOOTER: "page-footer",
    DocItemLabel.FOOTNOTE: "footnote",
    DocItemLabel.TABLE: "table",
    DocItemLabel.FORMULA: "equation",
    DocItemLabel.LIST_ITEM: "paragraph",
    DocItemLabel.CODE: "paragraph",
    DocItemLabel.PICTURE: "figure",
    DocItemLabel.TEXT: "paragraph",
    DocItemLabel.PARAGRAPH: "paragraph",
    DocItemLabel.FORM: DocItemLabel.FORM.value,
    DocItemLabel.KEY_VALUE_REGION: DocItemLabel.KEY_VALUE_REGION.value,
}

_EMPTY_DOCLING_DOC = DoclingDocument(name="dummy")


class InputDocument(BaseModel):
    file: PurePath
    document_hash: str  # = None
    valid: bool = True
    limits: DocumentLimits = DocumentLimits()
    format: InputFormat  # = None

    filesize: Optional[int] = None
    page_count: int = 0

    _backend: AbstractDocumentBackend  # Internal PDF backend used

    def __init__(
        self,
        path_or_stream: Union[BytesIO, Path],
        format: InputFormat,
        backend: Type[AbstractDocumentBackend],
        filename: Optional[str] = None,
        limits: Optional[DocumentLimits] = None,
    ):
        super().__init__(
            file="", document_hash="", format=InputFormat.PDF
        )  # initialize with dummy values

        self.limits = limits or DocumentLimits()
        self.format = format

        try:
            if isinstance(path_or_stream, Path):
                self.file = path_or_stream
                self.filesize = path_or_stream.stat().st_size
                if self.filesize > self.limits.max_file_size:
                    self.valid = False
                else:
                    self.document_hash = create_file_hash(path_or_stream)
                    self._init_doc(backend, path_or_stream)

            elif isinstance(path_or_stream, BytesIO):
                assert (
                    filename is not None
                ), "Can't construct InputDocument from stream without providing filename arg."
                self.file = PurePath(filename)
                self.filesize = path_or_stream.getbuffer().nbytes

                if self.filesize > self.limits.max_file_size:
                    self.valid = False
                else:
                    self.document_hash = create_file_hash(path_or_stream)
                    self._init_doc(backend, path_or_stream)
            else:
                raise RuntimeError(
                    f"Unexpected type path_or_stream: {type(path_or_stream)}"
                )

            # For paginated backends, check if the maximum page count is exceeded.
            if self.valid and self._backend.is_valid():
                if self._backend.supports_pagination() and isinstance(
                    self._backend, PaginatedDocumentBackend
                ):
                    self.page_count = self._backend.page_count()
                    if not self.page_count <= self.limits.max_num_pages:
                        self.valid = False

        except (FileNotFoundError, OSError) as e:
            self.valid = False
            _log.exception(
                f"File {self.file.name} not found or cannot be opened.", exc_info=e
            )
            # raise
        except RuntimeError as e:
            self.valid = False
            _log.exception(
                f"An unexpected error occurred while opening the document {self.file.name}",
                exc_info=e,
            )
            # raise

    def _init_doc(
        self,
        backend: Type[AbstractDocumentBackend],
        path_or_stream: Union[BytesIO, Path],
    ) -> None:
        self._backend = backend(self, path_or_stream=path_or_stream)
        if not self._backend.is_valid():
            self.valid = False


class DocumentFormat(str, Enum):
    V2 = "v2"
    V1 = "v1"


class ConversionResult(BaseModel):
    input: InputDocument

    status: ConversionStatus = ConversionStatus.PENDING  # failure, success
    errors: List[ErrorItem] = []  # structure to keep errors

    pages: List[Page] = []
    assembled: AssembledUnit = AssembledUnit()
    timings: Dict[str, ProfilingItem] = {}

    document: DoclingDocument = _EMPTY_DOCLING_DOC

    @property
    @deprecated("Use document instead.")
    def legacy_document(self):
        return docling_document_to_legacy(self.document)


class _DummyBackend(AbstractDocumentBackend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def is_valid(self) -> bool:
        return False

    @classmethod
    def supported_formats(cls) -> Set[InputFormat]:
        return set()

    @classmethod
    def supports_pagination(cls) -> bool:
        return False

    def unload(self):
        return super().unload()


class _DocumentConversionInput(BaseModel):

    path_or_stream_iterator: Iterable[Union[Path, str, DocumentStream]]
    limits: Optional[DocumentLimits] = DocumentLimits()

    def docs(
        self, format_options: Dict[InputFormat, "FormatOption"]
    ) -> Iterable[InputDocument]:
        for item in self.path_or_stream_iterator:
            obj = resolve_source_to_stream(item) if isinstance(item, str) else item
            format = self._guess_format(obj)
            backend: Type[AbstractDocumentBackend]
            if format not in format_options.keys():
                _log.error(
                    f"Input document {obj.name} does not match any allowed format."
                )
                backend = _DummyBackend
            else:
                backend = format_options[format].backend

            if isinstance(obj, Path):
                yield InputDocument(
                    path_or_stream=obj,
                    format=format,  # type: ignore[arg-type]
                    filename=obj.name,
                    limits=self.limits,
                    backend=backend,
                )
            elif isinstance(obj, DocumentStream):
                yield InputDocument(
                    path_or_stream=obj.stream,
                    format=format,  # type: ignore[arg-type]
                    filename=obj.name,
                    limits=self.limits,
                    backend=backend,
                )
            else:
                raise RuntimeError(f"Unexpected obj type in iterator: {type(obj)}")

    def _guess_format(self, obj: Union[Path, DocumentStream]) -> Optional[InputFormat]:
        content = b""  # empty binary blob
        formats: list[InputFormat] = []

        if isinstance(obj, Path):
            mime = filetype.guess_mime(str(obj))
            if mime is None:
                ext = obj.suffix[1:]
                mime = _DocumentConversionInput._mime_from_extension(ext)
            if mime is None:  # must guess from
                with obj.open("rb") as f:
                    content = f.read(1024)  # Read first 1KB

        elif isinstance(obj, DocumentStream):
            content = obj.stream.read(8192)
            obj.stream.seek(0)
            mime = filetype.guess_mime(content)
            if mime is None:
                ext = (
                    obj.name.rsplit(".", 1)[-1]
                    if ("." in obj.name and not obj.name.startswith("."))
                    else ""
                )
                mime = _DocumentConversionInput._mime_from_extension(ext)

        mime = mime or _DocumentConversionInput._detect_html_xhtml(content)
        mime = mime or "text/plain"
        formats = MimeTypeToFormat.get(mime, [])
        if formats:
            # TODO: remove application/xml case after adding another XML parse
            if len(formats) == 1 and mime not in ("text/plain", "application/xml"):
                return formats[0]
            else:  # ambiguity in formats
                return _DocumentConversionInput._guess_from_content(
                    content, mime, formats
                )
        else:
            return None

    @staticmethod
    def _guess_from_content(
        content: bytes, mime: str, formats: list[InputFormat]
    ) -> Optional[InputFormat]:
        """Guess the input format of a document by checking part of its content."""
        input_format: Optional[InputFormat] = None
        content_str = content.decode("utf-8")

        if mime == "application/xml":
            match_doctype = re.search(r"<!DOCTYPE [^>]+>", content_str)
            if match_doctype:
                xml_doctype = match_doctype.group()
                if InputFormat.XML_USPTO in formats and any(
                    item in xml_doctype
                    for item in (
                        "us-patent-application-v4",
                        "us-patent-grant-v4",
                        "us-grant-025",
                        "patent-application-publication",
                    )
                ):
                    input_format = InputFormat.XML_USPTO

        elif mime == "text/plain":
            if InputFormat.XML_USPTO in formats and content_str.startswith("PATN\r\n"):
                input_format = InputFormat.XML_USPTO

        return input_format

    @staticmethod
    def _mime_from_extension(ext):
        mime = None
        if ext in FormatToExtensions[InputFormat.ASCIIDOC]:
            mime = FormatToMimeType[InputFormat.ASCIIDOC][0]
        elif ext in FormatToExtensions[InputFormat.HTML]:
            mime = FormatToMimeType[InputFormat.HTML][0]
        elif ext in FormatToExtensions[InputFormat.MD]:
            mime = FormatToMimeType[InputFormat.MD][0]

        return mime

    @staticmethod
    def _detect_html_xhtml(
        content: bytes,
    ) -> Optional[Literal["application/xhtml+xml", "application/xml", "text/html"]]:
        """Guess the mime type of an XHTML, HTML, or XML file from its content.

        Args:
            content: A short piece of a document from its beginning.

        Returns:
            The mime type of an XHTML, HTML, or XML file, or None if the content does
              not match any of these formats.
        """
        content_str = content.decode("ascii", errors="ignore").lower()
        # Remove XML comments
        content_str = re.sub(r"<!--(.*?)-->", "", content_str, flags=re.DOTALL)
        content_str = content_str.lstrip()

        if re.match(r"<\?xml", content_str):
            if "xhtml" in content_str[:1000]:
                return "application/xhtml+xml"
            else:
                return "application/xml"

        if re.match(r"<!doctype\s+html|<html|<head|<body", content_str):
            return "text/html"

        return None
