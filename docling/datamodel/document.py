import logging
import re
from enum import Enum
from io import BytesIO
from pathlib import Path, PurePath
from typing import TYPE_CHECKING, Dict, Iterable, List, Optional, Type, Union

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
from docling_core.utils.file import resolve_file_source
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
    DocItemLabel.DOCUMENT_INDEX: "table-of-contents",
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
        if backend is None:
            raise RuntimeError(
                f"No backend configuration provided for file {self.file.name} with format {self.format}. "
                f"Please check your format configuration on DocumentConverter."
            )

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
        reverse_label_mapping = {
            DocItemLabel.CAPTION.value: "Caption",
            DocItemLabel.FOOTNOTE.value: "Footnote",
            DocItemLabel.FORMULA.value: "Formula",
            DocItemLabel.LIST_ITEM.value: "List-item",
            DocItemLabel.PAGE_FOOTER.value: "Page-footer",
            DocItemLabel.PAGE_HEADER.value: "Page-header",
            DocItemLabel.PICTURE.value: "Picture",  # low threshold adjust to capture chemical structures for examples.
            DocItemLabel.SECTION_HEADER.value: "Section-header",
            DocItemLabel.TABLE.value: "Table",
            DocItemLabel.TEXT.value: "Text",
            DocItemLabel.TITLE.value: "Title",
            DocItemLabel.DOCUMENT_INDEX.value: "Document Index",
            DocItemLabel.CODE.value: "Code",
            DocItemLabel.CHECKBOX_SELECTED.value: "Checkbox-Selected",
            DocItemLabel.CHECKBOX_UNSELECTED.value: "Checkbox-Unselected",
            DocItemLabel.FORM.value: "Form",
            DocItemLabel.KEY_VALUE_REGION.value: "Key-Value Region",
            DocItemLabel.PARAGRAPH.value: "paragraph",
        }

        title = ""
        desc = DsDocumentDescription(logs=[])

        page_hashes = [
            PageReference(
                hash=create_hash(self.input.document_hash + ":" + str(p.page_no - 1)),
                page=p.page_no,
                model="default",
            )
            for p in self.document.pages.values()
        ]

        file_info = DsFileInfoObject(
            filename=self.input.file.name,
            document_hash=self.input.document_hash,
            num_pages=self.input.page_count,
            page_hashes=page_hashes,
        )

        main_text = []
        tables = []
        figures = []
        equations = []
        footnotes = []
        page_headers = []
        page_footers = []

        embedded_captions = set()
        for ix, (item, level) in enumerate(
            self.document.iterate_items(self.document.body)
        ):

            if isinstance(item, (TableItem, PictureItem)) and len(item.captions) > 0:
                caption = item.caption_text(self.document)
                if caption:
                    embedded_captions.add(caption)

        for item, level in self.document.iterate_items():
            if isinstance(item, DocItem):
                item_type = item.label

                if isinstance(item, (TextItem, ListItem, SectionHeaderItem)):

                    if isinstance(item, ListItem) and item.marker:
                        text = f"{item.marker} {item.text}"
                    else:
                        text = item.text

                    # Can be empty.
                    prov = [
                        Prov(
                            bbox=p.bbox.as_tuple(),
                            page=p.page_no,
                            span=[0, len(item.text)],
                        )
                        for p in item.prov
                    ]
                    main_text.append(
                        BaseText(
                            text=text,
                            obj_type=layout_label_to_ds_type.get(item.label),
                            name=reverse_label_mapping[item.label],
                            prov=prov,
                        )
                    )

                    # skip captions of they are embedded in the actual
                    # floating object
                    if item_type == DocItemLabel.CAPTION and text in embedded_captions:
                        continue

                elif isinstance(item, TableItem) and item.data:
                    index = len(tables)
                    ref_str = f"#/tables/{index}"
                    main_text.append(
                        Ref(
                            name=reverse_label_mapping[item.label],
                            obj_type=layout_label_to_ds_type.get(item.label),
                            ref=ref_str,
                        ),
                    )

                    # Initialise empty table data grid (only empty cells)
                    table_data = [
                        [
                            TableCell(
                                text="",
                                # bbox=[0,0,0,0],
                                spans=[[i, j]],
                                obj_type="body",
                            )
                            for j in range(item.data.num_cols)
                        ]
                        for i in range(item.data.num_rows)
                    ]

                    # Overwrite cells in table data for which there is actual cell content.
                    for cell in item.data.table_cells:
                        for i in range(
                            min(cell.start_row_offset_idx, item.data.num_rows),
                            min(cell.end_row_offset_idx, item.data.num_rows),
                        ):
                            for j in range(
                                min(cell.start_col_offset_idx, item.data.num_cols),
                                min(cell.end_col_offset_idx, item.data.num_cols),
                            ):
                                celltype = "body"
                                if cell.column_header:
                                    celltype = "col_header"
                                elif cell.row_header:
                                    celltype = "row_header"
                                elif cell.row_section:
                                    celltype = "row_section"

                                def make_spans(cell):
                                    for rspan in range(
                                        min(
                                            cell.start_row_offset_idx,
                                            item.data.num_rows,
                                        ),
                                        min(
                                            cell.end_row_offset_idx, item.data.num_rows
                                        ),
                                    ):
                                        for cspan in range(
                                            min(
                                                cell.start_col_offset_idx,
                                                item.data.num_cols,
                                            ),
                                            min(
                                                cell.end_col_offset_idx,
                                                item.data.num_cols,
                                            ),
                                        ):
                                            yield [rspan, cspan]

                                spans = list(make_spans(cell))
                                table_data[i][j] = GlmTableCell(
                                    text=cell.text,
                                    bbox=(
                                        cell.bbox.as_tuple()
                                        if cell.bbox is not None
                                        else None
                                    ),  # check if this is bottom-left
                                    spans=spans,
                                    obj_type=celltype,
                                    col=j,
                                    row=i,
                                    row_header=cell.row_header,
                                    row_section=cell.row_section,
                                    col_header=cell.column_header,
                                    row_span=[
                                        cell.start_row_offset_idx,
                                        cell.end_row_offset_idx,
                                    ],
                                    col_span=[
                                        cell.start_col_offset_idx,
                                        cell.end_col_offset_idx,
                                    ],
                                )

                    # Compute the caption
                    caption = item.caption_text(self.document)

                    tables.append(
                        DsSchemaTable(
                            text=caption,
                            num_cols=item.data.num_cols,
                            num_rows=item.data.num_rows,
                            obj_type=layout_label_to_ds_type.get(item.label),
                            data=table_data,
                            prov=[
                                Prov(
                                    bbox=p.bbox.as_tuple(),
                                    page=p.page_no,
                                    span=[0, 0],
                                )
                                for p in item.prov
                            ],
                        )
                    )

                elif isinstance(item, PictureItem):
                    index = len(figures)
                    ref_str = f"#/figures/{index}"
                    main_text.append(
                        Ref(
                            name=reverse_label_mapping[item.label],
                            obj_type=layout_label_to_ds_type.get(item.label),
                            ref=ref_str,
                        ),
                    )

                    # Compute the caption
                    caption = item.caption_text(self.document)

                    figures.append(
                        Figure(
                            prov=[
                                Prov(
                                    bbox=p.bbox.as_tuple(),
                                    page=p.page_no,
                                    span=[0, len(caption)],
                                )
                                for p in item.prov
                            ],
                            obj_type=layout_label_to_ds_type.get(item.label),
                            text=caption,
                            # data=[[]],
                        )
                    )

        page_dimensions = [
            PageDimensions(page=p.page_no, height=p.size.height, width=p.size.width)
            for p in self.document.pages.values()
        ]

        ds_doc = DsDocument(
            name=title,
            description=desc,
            file_info=file_info,
            main_text=main_text,
            equations=equations,
            footnotes=footnotes,
            page_headers=page_headers,
            page_footers=page_footers,
            tables=tables,
            figures=figures,
            page_dimensions=page_dimensions,
        )

        return ds_doc


class _DocumentConversionInput(BaseModel):

    path_or_stream_iterator: Iterable[Union[Path, str, DocumentStream]]
    limits: Optional[DocumentLimits] = DocumentLimits()

    def docs(
        self, format_options: Dict[InputFormat, "FormatOption"]
    ) -> Iterable[InputDocument]:
        for item in self.path_or_stream_iterator:
            obj = resolve_file_source(item) if isinstance(item, str) else item
            format = self._guess_format(obj)
            if format not in format_options.keys():
                _log.info(
                    f"Skipping input document {obj.name} because it isn't matching any of the allowed formats."
                )
                continue
            else:
                backend = format_options[format].backend

            if isinstance(obj, Path):
                yield InputDocument(
                    path_or_stream=obj,
                    format=format,
                    filename=obj.name,
                    limits=self.limits,
                    backend=backend,
                )
            elif isinstance(obj, DocumentStream):
                yield InputDocument(
                    path_or_stream=obj.stream,
                    format=format,
                    filename=obj.name,
                    limits=self.limits,
                    backend=backend,
                )
            else:
                raise RuntimeError(f"Unexpected obj type in iterator: {type(obj)}")

    def _guess_format(self, obj: Union[Path, DocumentStream]):
        content = b""  # empty binary blob
        format = None

        if isinstance(obj, Path):
            mime = filetype.guess_mime(str(obj))
            if mime is None:
                ext = obj.suffix[1:]
                mime = self._mime_from_extension(ext)
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
                mime = self._mime_from_extension(ext)

        mime = mime or self._detect_html_xhtml(content)
        mime = mime or "text/plain"

        format = MimeTypeToFormat.get(mime)
        return format

    def _mime_from_extension(self, ext):
        mime = None
        if ext in FormatToExtensions[InputFormat.ASCIIDOC]:
            mime = FormatToMimeType[InputFormat.ASCIIDOC][0]
        elif ext in FormatToExtensions[InputFormat.HTML]:
            mime = FormatToMimeType[InputFormat.HTML][0]
        elif ext in FormatToExtensions[InputFormat.MD]:
            mime = FormatToMimeType[InputFormat.MD][0]

        return mime

    def _detect_html_xhtml(self, content):
        content_str = content.decode("ascii", errors="ignore").lower()
        # Remove XML comments
        content_str = re.sub(r"<!--(.*?)-->", "", content_str, flags=re.DOTALL)
        content_str = content_str.lstrip()

        if re.match(r"<\?xml", content_str):
            if "xhtml" in content_str[:1000]:
                return "application/xhtml+xml"

        if re.match(r"<!doctype\s+html|<html|<head|<body", content_str):
            return "text/html"

        return None
