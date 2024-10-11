from enum import Enum, auto
from typing import List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class TableFormerMode(str, Enum):
    FAST = auto()
    ACCURATE = auto()


class TableStructureOptions(BaseModel):
    do_cell_matching: bool = (
        True
        # True:  Matches predictions back to PDF cells. Can break table output if PDF cells
        #        are merged across table columns.
        # False: Let table structure model define the text cells, ignore PDF cells.
    )
    mode: TableFormerMode = TableFormerMode.FAST


class OcrOptions(BaseModel):
    kind: str


class EasyOcrOptions(OcrOptions):
    kind: Literal["easyocr"] = "easyocr"
    lang: List[str] = ["fr", "de", "es", "en"]
    use_gpu: bool = True  # same default as easyocr.Reader
    model_storage_directory: Optional[str] = None
    download_enabled: bool = True  # same default as easyocr.Reader

    model_config = ConfigDict(
        extra="forbid",
        protected_namespaces=(),
    )


class TesseractCliOcrOptions(OcrOptions):
    kind: Literal["tesseract"] = "tesseract"
    lang: List[str] = ["fra", "deu", "spa", "eng"]
    tesseract_cmd: str = "tesseract"
    path: Optional[str] = None

    model_config = ConfigDict(
        extra="forbid",
    )


class TesseractOcrOptions(OcrOptions):
    kind: Literal["tesserocr"] = "tesserocr"
    lang: List[str] = ["fra", "deu", "spa", "eng"]
    path: Optional[str] = None

    model_config = ConfigDict(
        extra="forbid",
    )


class PipelineOptions(BaseModel):
    do_table_structure: bool = True  # True: perform table structure extraction
    do_ocr: bool = True  # True: perform OCR, replace programmatic PDF text

    table_structure_options: TableStructureOptions = TableStructureOptions()
    ocr_options: Union[EasyOcrOptions, TesseractCliOcrOptions, TesseractOcrOptions] = (
        Field(EasyOcrOptions(), discriminator="kind")
    )
