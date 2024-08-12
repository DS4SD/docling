import copy
from enum import Enum, auto
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple, Union

from PIL.Image import Image
from pydantic import BaseModel, ConfigDict, model_validator

from docling.backend.abstract_backend import PdfPageBackend


class ConversionStatus(str, Enum):
    PENDING = auto()
    STARTED = auto()
    FAILURE = auto()
    SUCCESS = auto()
    SUCCESS_WITH_ERRORS = auto()


class DocInputType(str, Enum):
    PATH = auto()
    STREAM = auto()


class CoordOrigin(str, Enum):
    TOPLEFT = auto()
    BOTTOMLEFT = auto()


class PageSize(BaseModel):
    width: float = 0.0
    height: float = 0.0


class BoundingBox(BaseModel):
    l: float  # left
    t: float  # top
    r: float  # right
    b: float  # bottom

    coord_origin: CoordOrigin = CoordOrigin.TOPLEFT

    @property
    def width(self):
        return self.r - self.l

    @property
    def height(self):
        return abs(self.t - self.b)

    def scaled(self, scale: float) -> "BoundingBox":
        out_bbox = copy.deepcopy(self)
        out_bbox.l *= scale
        out_bbox.r *= scale
        out_bbox.t *= scale
        out_bbox.b *= scale

        return out_bbox

    def as_tuple(self):
        if self.coord_origin == CoordOrigin.TOPLEFT:
            return (self.l, self.t, self.r, self.b)
        elif self.coord_origin == CoordOrigin.BOTTOMLEFT:
            return (self.l, self.b, self.r, self.t)

    @classmethod
    def from_tuple(cls, coord: Tuple[float], origin: CoordOrigin):
        if origin == CoordOrigin.TOPLEFT:
            return BoundingBox(
                l=coord[0], t=coord[1], r=coord[2], b=coord[3], coord_origin=origin
            )
        elif origin == CoordOrigin.BOTTOMLEFT:
            return BoundingBox(
                l=coord[0], b=coord[1], r=coord[2], t=coord[3], coord_origin=origin
            )

    def area(self) -> float:
        return (self.r - self.l) * (self.b - self.t)

    def intersection_area_with(self, other: "BoundingBox") -> float:
        # Calculate intersection coordinates
        left = max(self.l, other.l)
        top = max(self.t, other.t)
        right = min(self.r, other.r)
        bottom = min(self.b, other.b)

        # Calculate intersection dimensions
        width = right - left
        height = bottom - top

        # If the bounding boxes do not overlap, width or height will be negative
        if width <= 0 or height <= 0:
            return 0.0

        return width * height

    def to_bottom_left_origin(self, page_height) -> "BoundingBox":
        if self.coord_origin == CoordOrigin.BOTTOMLEFT:
            return self
        elif self.coord_origin == CoordOrigin.TOPLEFT:
            return BoundingBox(
                l=self.l,
                r=self.r,
                t=page_height - self.t,
                b=page_height - self.b,
                coord_origin=CoordOrigin.BOTTOMLEFT,
            )

    def to_top_left_origin(self, page_height):
        if self.coord_origin == CoordOrigin.TOPLEFT:
            return self
        elif self.coord_origin == CoordOrigin.BOTTOMLEFT:
            return BoundingBox(
                l=self.l,
                r=self.r,
                t=page_height - self.t,  # self.b
                b=page_height - self.b,  # self.t
                coord_origin=CoordOrigin.TOPLEFT,
            )


class Cell(BaseModel):
    id: int
    text: str
    bbox: BoundingBox


class OcrCell(Cell):
    confidence: float


class Cluster(BaseModel):
    id: int
    label: str
    bbox: BoundingBox
    confidence: float = 1.0
    cells: List[Cell] = []


class BasePageElement(BaseModel):
    label: str
    id: int
    page_no: int
    cluster: Cluster
    text: Optional[str] = None


class LayoutPrediction(BaseModel):
    clusters: List[Cluster] = []


class TableCell(BaseModel):
    bbox: BoundingBox
    row_span: int
    col_span: int
    start_row_offset_idx: int
    end_row_offset_idx: int
    start_col_offset_idx: int
    end_col_offset_idx: int
    text: str
    column_header: bool = False
    row_header: bool = False
    row_section: bool = False

    @model_validator(mode="before")
    @classmethod
    def from_dict_format(cls, data: Any) -> Any:
        if isinstance(data, Dict):
            text = data["bbox"].get("token", "")
            if not len(text):
                text_cells = data.pop("text_cell_bboxes", None)
                if text_cells:
                    for el in text_cells:
                        text += el["token"] + " "

                text = text.strip()
            data["text"] = text

        return data


class TableElement(BasePageElement):
    otsl_seq: List[str]
    num_rows: int = 0
    num_cols: int = 0
    table_cells: List[TableCell]


class TableStructurePrediction(BaseModel):
    table_map: Dict[int, TableElement] = {}


class TextElement(BasePageElement): ...


class FigureData(BaseModel):
    pass


class FigureElement(BasePageElement):
    data: Optional[FigureData] = None
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
    layout: LayoutPrediction = None
    tablestructure: TableStructurePrediction = None
    figures_classification: FigureClassificationPrediction = None
    equations_prediction: EquationPrediction = None


PageElement = Union[TextElement, TableElement, FigureElement]


class AssembledUnit(BaseModel):
    elements: List[PageElement]
    body: List[PageElement]
    headers: List[PageElement]


class Page(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    page_no: int
    page_hash: str = None
    size: PageSize = None
    image: Image = None
    cells: List[Cell] = None
    predictions: PagePredictions = PagePredictions()
    assembled: AssembledUnit = None

    _backend: PdfPageBackend = None  # Internal PDF backend


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
    do_ocr: bool = False  # True: perform OCR, replace programmatic PDF text

    table_structure_options: TableStructureOptions = TableStructureOptions()


class AssembleOptions(BaseModel):
    keep_page_images: bool = (
        False  # False: page images are removed in the assemble step
    )
