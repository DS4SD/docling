import copy
import warnings
from enum import Enum, auto
from io import BytesIO
from typing import Annotated, Any, Dict, List, Optional, Tuple, Union

from docling_core.types.experimental import BoundingBox, Size
from docling_core.types.experimental.document import BasePictureData, TableCell
from docling_core.types.experimental.labels import DocItemLabel
from PIL.Image import Image
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing_extensions import Self

from docling.backend.abstract_backend import PdfPageBackend


class ConversionStatus(str, Enum):
    PENDING = auto()
    STARTED = auto()
    FAILURE = auto()
    SUCCESS = auto()
    PARTIAL_SUCCESS = auto()


class DocInputType(str, Enum):
    PATH = auto()
    STREAM = auto()


class DoclingComponentType(str, Enum):
    PDF_BACKEND = auto()
    MODEL = auto()
    DOC_ASSEMBLER = auto()


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


class TextElement(BasePageElement): ...


class FigureElement(BasePageElement):
    data: Optional[BasePictureData] = None
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
    page_hash: Optional[str] = None
    size: Optional[Size] = None
    cells: List[Cell] = []
    predictions: PagePredictions = PagePredictions()
    assembled: Optional[AssembledUnit] = None

    _backend: Optional[PdfPageBackend] = (
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


class DocumentStream(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    filename: str
    stream: BytesIO


class TableStructureOptions(BaseModel):
    do_cell_matching: bool = (
        True
        # True:  Matches predictions back to PDF cells. Can break table output if PDF cells
        #        are merged across table columns.
        # False: Let table structure model define the text cells, ignore PDF cells.
    )


class PipelineOptions(BaseModel):
    do_table_structure: bool = True  # True: perform table structure extraction
    do_ocr: bool = True  # True: perform OCR, replace programmatic PDF text

    table_structure_options: TableStructureOptions = TableStructureOptions()


class AssembleOptions(BaseModel):
    keep_page_images: Annotated[
        bool,
        Field(
            deprecated="`keep_page_images` is depreacted, set the value of `images_scale` instead"
        ),
    ] = False  # False: page images are removed in the assemble step
    images_scale: Optional[float] = None  # if set, the scale for generated images

    @model_validator(mode="after")
    def set_page_images_from_deprecated(self) -> Self:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            default_scale = 1.0
            if self.keep_page_images and self.images_scale is None:
                self.images_scale = default_scale
        return self
