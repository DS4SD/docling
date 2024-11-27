from enum import Enum
from pathlib import Path
from typing import List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class TableFormerMode(str, Enum):
    FAST = "fast"
    ACCURATE = "accurate"


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
    lang: List[str]
    force_full_page_ocr: bool = False  # If enabled a full page OCR is always applied
    bitmap_area_threshold: float = (
        0.05  # percentage of the area for a bitmap to processed with OCR
    )


class RapidOcrOptions(OcrOptions):
    kind: Literal["rapidocr"] = "rapidocr"

    # English and chinese are the most commly used models and have been tested with RapidOCR.
    lang: List[str] = [
        "english",
        "chinese",
    ]  # However, language as a parameter is not supported by rapidocr yet and hence changing this options doesn't affect anything.
    # For more details on supported languages by RapidOCR visit https://rapidai.github.io/RapidOCRDocs/blog/2022/09/28/%E6%94%AF%E6%8C%81%E8%AF%86%E5%88%AB%E8%AF%AD%E8%A8%80/

    # For more details on the following options visit https://rapidai.github.io/RapidOCRDocs/install_usage/api/RapidOCR/
    text_score: float = 0.5  # same default as rapidocr

    use_det: Optional[bool] = None  # same default as rapidocr
    use_cls: Optional[bool] = None  # same default as rapidocr
    use_rec: Optional[bool] = None  # same default as rapidocr

    # class Device(Enum):
    #     CPU = "CPU"
    #     CUDA = "CUDA"
    #     DIRECTML = "DIRECTML"
    #     AUTO = "AUTO"

    # device: Device = Device.AUTO  # Default value is AUTO

    print_verbose: bool = False  # same default as rapidocr

    det_model_path: Optional[str] = None  # same default as rapidocr
    cls_model_path: Optional[str] = None  # same default as rapidocr
    rec_model_path: Optional[str] = None  # same default as rapidocr

    model_config = ConfigDict(
        extra="forbid",
    )


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


class OcrMacOptions(OcrOptions):
    kind: Literal["ocrmac"] = "ocrmac"
    lang: List[str] = ["fr-FR", "de-DE", "es-ES", "en-US"]
    recognition: str = "accurate"
    framework: str = "vision"

    model_config = ConfigDict(
        extra="forbid",
    )


class PipelineOptions(BaseModel):
    create_legacy_output: bool = (
        True  # This defautl will be set to False on a future version of docling
    )


class PdfPipelineOptions(PipelineOptions):
    artifacts_path: Optional[Union[Path, str]] = None
    do_table_structure: bool = True  # True: perform table structure extraction
    do_ocr: bool = True  # True: perform OCR, replace programmatic PDF text

    table_structure_options: TableStructureOptions = TableStructureOptions()
    ocr_options: Union[
        EasyOcrOptions, TesseractCliOcrOptions, TesseractOcrOptions, OcrMacOptions
    ] = Field(EasyOcrOptions(), discriminator="kind")

    images_scale: float = 1.0
    generate_page_images: bool = False
    generate_picture_images: bool = False
    generate_table_images: bool = Field(
        default=False,
        deprecated=(
            "Field `generate_table_images` is deprecated. "
            "To obtain table images, set `PdfPipelineOptions.generate_page_images = True` "
            "before conversion and then use the `TableItem.get_image` function."
        ),
    )
