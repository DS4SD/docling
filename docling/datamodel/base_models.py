import copy
import warnings
from enum import Enum, auto
from io import BytesIO
from typing import Annotated, Any, Dict, List, Optional, Tuple, Union

from PIL.Image import Image
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing_extensions import Self

from docling.backend.abstract_backend import PdfPageBackend
from docling.datamodel.pipeline_options import (  # Must be imported here for backward compatibility.
    PipelineOptions,
    TableStructureOptions,
)


class ConversionStatus(str, Enum):
    PENDING = auto()
    STARTED = auto()
    FAILURE = auto()
    SUCCESS = auto()
    PARTIAL_SUCCESS = auto()


class DocInputType(str, Enum):
    PATH = auto()
    STREAM = auto()


class CoordOrigin(str, Enum):
    TOPLEFT = auto()
    BOTTOMLEFT = auto()


class DoclingComponentType(str, Enum):
    PDF_BACKEND = auto()
    MODEL = auto()
    DOC_ASSEMBLER = auto()


class ErrorItem(BaseModel):
    component_type: DoclingComponentType
    module_name: str
    error_message: str


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

    def normalized(self, page_size: PageSize) -> "BoundingBox":
        out_bbox = copy.deepcopy(self)
        out_bbox.l /= page_size.width
        out_bbox.r /= page_size.width
        out_bbox.t /= page_size.height
        out_bbox.b /= page_size.height

        return out_bbox

    def as_tuple(self):
        if self.coord_origin == CoordOrigin.TOPLEFT:
            return (self.l, self.t, self.r, self.b)
        elif self.coord_origin == CoordOrigin.BOTTOMLEFT:
            return (self.l, self.b, self.r, self.t)

    @classmethod
    def from_tuple(cls, coord: Tuple[float, ...], origin: CoordOrigin):
        if origin == CoordOrigin.TOPLEFT:
            l, t, r, b = coord[0], coord[1], coord[2], coord[3]
            if r < l:
                l, r = r, l
            if b < t:
                b, t = t, b

            return BoundingBox(l=l, t=t, r=r, b=b, coord_origin=origin)
        elif origin == CoordOrigin.BOTTOMLEFT:
            l, b, r, t = coord[0], coord[1], coord[2], coord[3]
            if r < l:
                l, r = r, l
            if b > t:
                b, t = t, b

            return BoundingBox(l=l, t=t, r=r, b=b, coord_origin=origin)

    def area(self) -> float:
        area = (self.r - self.l) * (self.b - self.t)
        if self.coord_origin == CoordOrigin.BOTTOMLEFT:
            area = -area
        return area

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
    layout: Optional[LayoutPrediction] = None
    tablestructure: Optional[TableStructurePrediction] = None
    figures_classification: Optional[FigureClassificationPrediction] = None
    equations_prediction: Optional[EquationPrediction] = None


PageElement = Union[TextElement, TableElement, FigureElement]


class AssembledUnit(BaseModel):
    elements: List[PageElement] = []
    body: List[PageElement] = []
    headers: List[PageElement] = []


class Page(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    page_no: int
    page_hash: Optional[str] = None
    size: Optional[PageSize] = None
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
