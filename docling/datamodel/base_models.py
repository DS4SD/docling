from enum import Enum, auto
from typing import TYPE_CHECKING, Dict, List, Optional, Union

from docling_core.types.doc import (
    BoundingBox,
    DocItemLabel,
    PictureDataType,
    Size,
    TableCell,
)
from docling_core.types.io import (  # DO ΝΟΤ REMOVE; explicitly exposed from this location
    DocumentStream,
)
from PIL.Image import Image
from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from docling.backend.pdf_backend import PdfPageBackend


class ConversionStatus(str, Enum):
    PENDING = "pending"
    STARTED = "started"
    FAILURE = "failure"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    SKIPPED = "skipped"


class InputFormat(str, Enum):
    DOCX = "docx"
    PPTX = "pptx"
    HTML = "html"
    IMAGE = "image"
    PDF = "pdf"
    ASCIIDOC = "asciidoc"
    MD = "md"
    XLSX = "xlsx"
    XML_USPTO = "uspto"


class OutputFormat(str, Enum):
    MARKDOWN = "md"
    JSON = "json"
    HTML = "html"
    TEXT = "text"
    DOCTAGS = "doctags"


FormatToExtensions: Dict[InputFormat, List[str]] = {
    InputFormat.DOCX: ["docx", "dotx", "docm", "dotm"],
    InputFormat.PPTX: ["pptx", "potx", "ppsx", "pptm", "potm", "ppsm"],
    InputFormat.PDF: ["pdf"],
    InputFormat.MD: ["md"],
    InputFormat.HTML: ["html", "htm", "xhtml"],
    InputFormat.IMAGE: ["jpg", "jpeg", "png", "tif", "tiff", "bmp"],
    InputFormat.ASCIIDOC: ["adoc", "asciidoc", "asc"],
    InputFormat.XLSX: ["xlsx"],
    InputFormat.XML_USPTO: ["xml", "txt"],
}

FormatToMimeType: Dict[InputFormat, List[str]] = {
    InputFormat.DOCX: [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.template",
    ],
    InputFormat.PPTX: [
        "application/vnd.openxmlformats-officedocument.presentationml.template",
        "application/vnd.openxmlformats-officedocument.presentationml.slideshow",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ],
    InputFormat.HTML: ["text/html", "application/xhtml+xml"],
    InputFormat.IMAGE: [
        "image/png",
        "image/jpeg",
        "image/tiff",
        "image/gif",
        "image/bmp",
    ],
    InputFormat.PDF: ["application/pdf"],
    InputFormat.ASCIIDOC: ["text/asciidoc"],
    InputFormat.MD: ["text/markdown", "text/x-markdown"],
    InputFormat.XLSX: [
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ],
    InputFormat.XML_USPTO: ["application/xml", "text/plain"],
}

MimeTypeToFormat = {
    mime: fmt for fmt, mimes in FormatToMimeType.items() for mime in mimes
}


class DocInputType(str, Enum):
    PATH = "path"
    STREAM = "stream"


class DoclingComponentType(str, Enum):
    DOCUMENT_BACKEND = "document_backend"
    MODEL = "model"
    DOC_ASSEMBLER = "doc_assembler"
    USER_INPUT = "user_input"


class ErrorItem(BaseModel):
    component_type: DoclingComponentType
    module_name: str
    error_message: str


class Cell(BaseModel):
    id: int
    text: str
    bbox: BoundingBox


class OcrCell(Cell):
    confidence: float


class Cluster(BaseModel):
    id: int
    label: DocItemLabel
    bbox: BoundingBox
    confidence: float = 1.0
    cells: List[Cell] = []


class BasePageElement(BaseModel):
    label: DocItemLabel
    id: int
    page_no: int
    cluster: Cluster
    text: Optional[str] = None


class LayoutPrediction(BaseModel):
    clusters: List[Cluster] = []


class Table(BasePageElement):
    otsl_seq: List[str]
    num_rows: int = 0
    num_cols: int = 0
    table_cells: List[TableCell]


class TableStructurePrediction(BaseModel):
    table_map: Dict[int, Table] = {}


class TextElement(BasePageElement):
    text: str


class FigureElement(BasePageElement):
    annotations: List[PictureDataType] = []
    provenance: Optional[str] = None
    predicted_class: Optional[str] = None
    confidence: Optional[float] = None


class FigureClassificationPrediction(BaseModel):
    figure_count: int = 0
    figure_map: Dict[int, FigureElement] = {}


class EquationPrediction(BaseModel):
    equation_count: int = 0
    equation_map: Dict[int, TextElement] = {}


class PagePredictions(BaseModel):
    layout: Optional[LayoutPrediction] = None
    tablestructure: Optional[TableStructurePrediction] = None
    figures_classification: Optional[FigureClassificationPrediction] = None
    equations_prediction: Optional[EquationPrediction] = None


PageElement = Union[TextElement, Table, FigureElement]


class AssembledUnit(BaseModel):
    elements: List[PageElement] = []
    body: List[PageElement] = []
    headers: List[PageElement] = []


class Page(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    page_no: int
    # page_hash: Optional[str] = None
    size: Optional[Size] = None
    cells: List[Cell] = []
    predictions: PagePredictions = PagePredictions()
    assembled: Optional[AssembledUnit] = None

    _backend: Optional["PdfPageBackend"] = (
        None  # Internal PDF backend. By default it is cleared during assembling.
    )
    _default_image_scale: float = 1.0  # Default image scale for external usage.
    _image_cache: Dict[float, Image] = (
        {}
    )  # Cache of images in different scales. By default it is cleared during assembling.

    def get_image(self, scale: float = 1.0) -> Optional[Image]:
        if self._backend is None:
            return self._image_cache.get(scale, None)
        if not scale in self._image_cache:
            self._image_cache[scale] = self._backend.get_page_image(scale=scale)
        return self._image_cache[scale]

    @property
    def image(self) -> Optional[Image]:
        return self.get_image(scale=self._default_image_scale)
