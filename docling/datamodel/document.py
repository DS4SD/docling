import logging
import re
from enum import Enum
from io import BytesIO
from pathlib import Path, PurePath
from typing import Dict, Iterable, List, Optional, Tuple, Type, Union

import filetype
from docling_core.types import BaseText
from docling_core.types import Document as DsDocument
from docling_core.types import DocumentDescription as DsDocumentDescription
from docling_core.types import FileInfoObject as DsFileInfoObject
from docling_core.types import PageDimensions, PageReference, Prov, Ref
from docling_core.types import Table as DsSchemaTable
from docling_core.types.doc.base import BoundingBox as DsBoundingBox
from docling_core.types.doc.base import Figure, TableCell
from docling_core.types.experimental import (
    DescriptionItem,
    DocItemLabel,
    DoclingDocument,
)
from docling_core.utils.file import resolve_file_source
from pydantic import BaseModel
from typing_extensions import deprecated

from docling.backend.abstract_backend import AbstractDocumentBackend
from docling.backend.docling_parse_backend import DoclingParseDocumentBackend
from docling.backend.html_backend import HTMLDocumentBackend
from docling.backend.mspowerpoint_backend import MsPowerpointDocumentBackend
from docling.backend.msword_backend import MsWordDocumentBackend
from docling.datamodel.base_models import (
    AssembledUnit,
    ConversionStatus,
    DocumentStream,
    ErrorItem,
    FigureElement,
    InputFormat,
    MimeTypeToFormat,
    Page,
    PageElement,
    Table,
    TextElement,
)
from docling.datamodel.settings import DocumentLimits
from docling.utils.utils import create_file_hash, create_hash

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
}

_EMPTY_LEGACY_DOC = DsDocument(
    _name="",
    description=DsDocumentDescription(logs=[]),
    file_info=DsFileInfoObject(
        filename="",
        document_hash="",
    ),
)

_EMPTY_DOCLING_DOC = DoclingDocument(
    description=DescriptionItem(), name="dummy"
)  # TODO: Stub


class InputDocument(BaseModel):
    file: PurePath = None
    document_hash: Optional[str] = None
    valid: bool = True
    limits: DocumentLimits = DocumentLimits()
    format: Optional[InputFormat] = None

    filesize: Optional[int] = None
    page_count: int = 0

    _backend: AbstractDocumentBackend = None  # Internal PDF backend used

    def __init__(
        self,
        path_or_stream: Union[BytesIO, Path],
        format: InputFormat,
        backend: AbstractDocumentBackend,
        filename: Optional[str] = None,
        limits: Optional[DocumentLimits] = None,
    ):
        super().__init__()

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
                self.file = PurePath(filename)
                self.filesize = path_or_stream.getbuffer().nbytes

                if self.filesize > self.limits.max_file_size:
                    self.valid = False
                else:
                    self.document_hash = create_file_hash(path_or_stream)
                    self._init_doc(backend, path_or_stream)

            # For paginated backends, check if the maximum page count is exceeded.
            if self.valid and self._backend.is_valid():
                if self._backend.supports_pagination():
                    self.page_count = self._backend.page_count()
                    if not self.page_count <= self.limits.max_num_pages:
                        self.valid = False

        except (FileNotFoundError, OSError) as e:
            _log.exception(
                f"File {self.file.name} not found or cannot be opened.", exc_info=e
            )
            # raise
        except RuntimeError as e:
            _log.exception(
                f"An unexpected error occurred while opening the document {self.file.name}",
                exc_info=e,
            )
            # raise

    def _init_doc(
        self,
        backend: AbstractDocumentBackend,
        path_or_stream: Union[BytesIO, Path],
    ) -> None:
        if backend is None:
            raise RuntimeError(
                f"No backend configuration provided for file {self.file} with format {self.format}. "
                f"Please check your format configuration on DocumentConverter."
            )

        self._backend = backend(
            path_or_stream=path_or_stream, document_hash=self.document_hash
        )


class DocumentFormat(str, Enum):
    V2 = "v2"
    V1 = "v1"


class ConversionResult(BaseModel):
    input: InputDocument

    status: ConversionStatus = ConversionStatus.PENDING  # failure, success
    errors: List[ErrorItem] = []  # structure to keep errors

    pages: List[Page] = []
    assembled: AssembledUnit = AssembledUnit()

    legacy_output: Optional[DsDocument] = None  # _EMPTY_LEGACY_DOC
    output: DoclingDocument = _EMPTY_DOCLING_DOC

    def _to_legacy_document(self) -> DsDocument:
        title = ""
        desc = DsDocumentDescription(logs=[])

        page_hashes = [
            PageReference(
                hash=create_hash(self.input.document_hash + ":" + str(p.page_no)),
                page=p.page_no + 1,
                model="default",
            )
            for p in self.pages
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

        page_no_to_page = {p.page_no: p for p in self.pages}

        for element in self.assembled.elements:
            # Convert bboxes to lower-left origin.
            target_bbox = DsBoundingBox(
                element.cluster.bbox.to_bottom_left_origin(
                    page_no_to_page[element.page_no].size.height
                ).as_tuple()
            )

            if isinstance(element, TextElement):
                main_text.append(
                    BaseText(
                        text=element.text,
                        obj_type=layout_label_to_ds_type.get(element.label),
                        name=element.label,
                        prov=[
                            Prov(
                                bbox=target_bbox,
                                page=element.page_no + 1,
                                span=[0, len(element.text)],
                            )
                        ],
                    )
                )
            elif isinstance(element, Table):
                index = len(tables)
                ref_str = f"#/tables/{index}"
                main_text.append(
                    Ref(
                        name=element.label,
                        obj_type=layout_label_to_ds_type.get(element.label),
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
                        for j in range(element.num_cols)
                    ]
                    for i in range(element.num_rows)
                ]

                # Overwrite cells in table data for which there is actual cell content.
                for cell in element.table_cells:
                    for i in range(
                        min(cell.start_row_offset_idx, element.num_rows),
                        min(cell.end_row_offset_idx, element.num_rows),
                    ):
                        for j in range(
                            min(cell.start_col_offset_idx, element.num_cols),
                            min(cell.end_col_offset_idx, element.num_cols),
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
                                    min(cell.start_row_offset_idx, element.num_rows),
                                    min(cell.end_row_offset_idx, element.num_rows),
                                ):
                                    for cspan in range(
                                        min(
                                            cell.start_col_offset_idx, element.num_cols
                                        ),
                                        min(cell.end_col_offset_idx, element.num_cols),
                                    ):
                                        yield [rspan, cspan]

                            spans = list(make_spans(cell))
                            table_data[i][j] = TableCell(
                                text=cell.text,
                                bbox=cell.bbox.to_bottom_left_origin(
                                    page_no_to_page[element.page_no].size.height
                                ).as_tuple(),
                                # col=j,
                                # row=i,
                                spans=spans,
                                obj_type=celltype,
                                # col_span=[cell.start_col_offset_idx, cell.end_col_offset_idx],
                                # row_span=[cell.start_row_offset_idx, cell.end_row_offset_idx]
                            )

                tables.append(
                    DsSchemaTable(
                        num_cols=element.num_cols,
                        num_rows=element.num_rows,
                        obj_type=layout_label_to_ds_type.get(element.label),
                        data=table_data,
                        prov=[
                            Prov(
                                bbox=target_bbox,
                                page=element.page_no + 1,
                                span=[0, 0],
                            )
                        ],
                    )
                )

            elif isinstance(element, FigureElement):
                index = len(figures)
                ref_str = f"#/figures/{index}"
                main_text.append(
                    Ref(
                        name=element.label,
                        obj_type=layout_label_to_ds_type.get(element.label),
                        ref=ref_str,
                    ),
                )
                figures.append(
                    Figure(
                        prov=[
                            Prov(
                                bbox=target_bbox,
                                page=element.page_no + 1,
                                span=[0, 0],
                            )
                        ],
                        obj_type=layout_label_to_ds_type.get(element.label),
                        # data=[[]],
                    )
                )

        page_dimensions = [
            PageDimensions(page=p.page_no + 1, height=p.size.height, width=p.size.width)
            for p in self.pages
        ]

        ds_doc = DsDocument(
            name=title,
            description=desc,
            file_info=file_info,
            main_text=main_text,
            tables=tables,
            figures=figures,
            page_dimensions=page_dimensions,
        )

        return ds_doc

    @deprecated("Use output.export_to_dict() instead.")
    def render_as_dict(self):
        return self.legacy_output.model_dump(by_alias=True, exclude_none=True)

    @deprecated("Use output.export_to_markdown() instead.")
    def render_as_markdown(
        self,
        delim: str = "\n\n",
        main_text_start: int = 0,
        main_text_stop: Optional[int] = None,
        main_text_labels: list[str] = [
            "title",
            "subtitle-level-1",
            "paragraph",
            "caption",
            "table",
            "figure",
        ],
        strict_text: bool = False,
        image_placeholder: str = "<!-- image -->",
    ) -> str:
        return self.legacy_output.export_to_markdown(
            delim=delim,
            main_text_start=main_text_start,
            main_text_stop=main_text_stop,
            main_text_labels=main_text_labels,
            strict_text=strict_text,
            image_placeholder=image_placeholder,
        )

    @deprecated("Use output.export_to_text() instead.")
    def render_as_text(
        self,
        delim: str = "\n\n",
        main_text_start: int = 0,
        main_text_stop: Optional[int] = None,
        main_text_labels: list[str] = [
            "title",
            "subtitle-level-1",
            "paragraph",
            "caption",
        ],
    ) -> str:
        return self.legacy_output.export_to_markdown(
            delim=delim,
            main_text_start=main_text_start,
            main_text_stop=main_text_stop,
            main_text_labels=main_text_labels,
            strict_text=True,
        )

    @deprecated("Use output.export_to_document_tokens() instead.")
    def render_as_doctags(
        self,
        delim: str = "\n\n",
        main_text_start: int = 0,
        main_text_stop: Optional[int] = None,
        main_text_labels: list[str] = [
            "title",
            "subtitle-level-1",
            "paragraph",
            "caption",
            "table",
            "figure",
        ],
        xsize: int = 100,
        ysize: int = 100,
        add_location: bool = True,
        add_content: bool = True,
        add_page_index: bool = True,
        # table specific flags
        add_table_cell_location: bool = False,
        add_table_cell_label: bool = True,
        add_table_cell_text: bool = True,
    ) -> str:
        return self.legacy_output.export_to_document_tokens(
            delim=delim,
            main_text_start=main_text_start,
            main_text_stop=main_text_stop,
            main_text_labels=main_text_labels,
            xsize=xsize,
            ysize=ysize,
            add_location=add_location,
            add_content=add_content,
            add_page_index=add_page_index,
            # table specific flags
            add_table_cell_location=add_table_cell_location,
            add_table_cell_label=add_table_cell_label,
            add_table_cell_text=add_table_cell_text,
        )

    def render_element_images(
        self, element_types: Tuple[PageElement] = (FigureElement,)
    ):
        for element in self.assembled.elements:
            if isinstance(element, element_types):
                page_ix = element.page_no
                scale = self.pages[page_ix]._default_image_scale
                crop_bbox = element.cluster.bbox.scaled(scale=scale).to_top_left_origin(
                    page_height=self.pages[page_ix].size.height * scale
                )

                cropped_im = self.pages[page_ix].image.crop(crop_bbox.as_tuple())
                yield element, cropped_im


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
                _log.debug(
                    f"Skipping input document {obj.name} because its format is not in the whitelist."
                )
                continue
            else:
                backend = format_options.get(format).backend

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

    def _guess_format(self, obj):
        content = None
        if isinstance(obj, Path):
            mime = filetype.guess_mime(str(obj))
            if mime is None:
                with obj.open("rb") as f:
                    content = f.read(1024)  # Read first 1KB

        elif isinstance(obj, DocumentStream):
            obj.stream.seek(0)
            content = obj.stream.read(8192)
            obj.stream.seek(0)
            mime = filetype.guess_mime(content)

        if mime is None:
            mime = self._detect_html_xhtml(content)

        format = MimeTypeToFormat.get(mime)
        return format

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
