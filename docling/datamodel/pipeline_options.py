import logging
import os
import warnings
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Dict, List, Literal, Optional, Tuple, Type, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)
from typing_extensions import deprecated

_log = logging.getLogger(__name__)


class AcceleratorDevice(str, Enum):
    """Devices to run model inference"""

    AUTO = "auto"
    CPU = "cpu"
    CUDA = "cuda"
    MPS = "mps"


class AcceleratorOptions(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DOCLING_", env_nested_delimiter="_", populate_by_name=True
    )

    num_threads: int = 4
    device: AcceleratorDevice = AcceleratorDevice.AUTO

    @model_validator(mode="before")
    @classmethod
    def check_alternative_envvars(cls, data: Any) -> Any:
        r"""
        Set num_threads from the "alternative" envvar OMP_NUM_THREADS.
        The alternative envvar is used only if it is valid and the regular envvar is not set.

        Notice: The standard pydantic settings mechanism with parameter "aliases" does not provide
        the same functionality. In case the alias envvar is set and the user tries to override the
        parameter in settings initialization, Pydantic treats the parameter provided in __init__()
        as an extra input instead of simply overwriting the evvar value for that parameter.
        """
        if isinstance(data, dict):
            input_num_threads = data.get("num_threads")

            # Check if to set the num_threads from the alternative envvar
            if input_num_threads is None:
                docling_num_threads = os.getenv("DOCLING_NUM_THREADS")
                omp_num_threads = os.getenv("OMP_NUM_THREADS")
                if docling_num_threads is None and omp_num_threads is not None:
                    try:
                        data["num_threads"] = int(omp_num_threads)
                    except ValueError:
                        _log.error(
                            "Ignoring misformatted envvar OMP_NUM_THREADS '%s'",
                            omp_num_threads,
                        )
        return data


class TableFormerMode(str, Enum):
    """Modes for the TableFormer model."""

    FAST = "fast"
    ACCURATE = "accurate"


class TableStructureOptions(BaseModel):
    """Options for the table structure."""

    do_cell_matching: bool = (
        True
        # True:  Matches predictions back to PDF cells. Can break table output if PDF cells
        #        are merged across table columns.
        # False: Let table structure model define the text cells, ignore PDF cells.
    )
    mode: TableFormerMode = TableFormerMode.FAST


class OcrOptions(BaseModel):
    """OCR options."""

    kind: str
    lang: List[str]
    force_full_page_ocr: bool = False  # If enabled a full page OCR is always applied
    bitmap_area_threshold: float = (
        0.05  # percentage of the area for a bitmap to processed with OCR
    )


class RapidOcrOptions(OcrOptions):
    """Options for the RapidOCR engine."""

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
    """Options for the EasyOCR engine."""

    kind: Literal["easyocr"] = "easyocr"
    lang: List[str] = ["fr", "de", "es", "en"]

    use_gpu: Optional[bool] = None

    confidence_threshold: float = 0.5

    model_storage_directory: Optional[str] = None
    recog_network: Optional[str] = "standard"
    download_enabled: bool = True

    model_config = ConfigDict(
        extra="forbid",
        protected_namespaces=(),
    )


class TesseractCliOcrOptions(OcrOptions):
    """Options for the TesseractCli engine."""

    kind: Literal["tesseract"] = "tesseract"
    lang: List[str] = ["fra", "deu", "spa", "eng"]
    tesseract_cmd: str = "tesseract"
    path: Optional[str] = None

    model_config = ConfigDict(
        extra="forbid",
    )


class TesseractOcrOptions(OcrOptions):
    """Options for the Tesseract engine."""

    kind: Literal["tesserocr"] = "tesserocr"
    lang: List[str] = ["fra", "deu", "spa", "eng"]
    path: Optional[str] = None

    model_config = ConfigDict(
        extra="forbid",
    )


class OcrMacOptions(OcrOptions):
    """Options for the Mac OCR engine."""

    kind: Literal["ocrmac"] = "ocrmac"
    lang: List[str] = ["fr-FR", "de-DE", "es-ES", "en-US"]
    recognition: str = "accurate"
    framework: str = "vision"

    model_config = ConfigDict(
        extra="forbid",
    )


# Define an enum for the backend options
class PdfBackend(str, Enum):
    """Enum of valid PDF backends."""

    PYPDFIUM2 = "pypdfium2"
    DLPARSE_V1 = "dlparse_v1"
    DLPARSE_V2 = "dlparse_v2"


# Define an enum for the ocr engines
class OcrEngine(str, Enum):
    """Enum of valid OCR engines."""

    EASYOCR = "easyocr"
    TESSERACT_CLI = "tesseract_cli"
    TESSERACT = "tesseract"
    OCRMAC = "ocrmac"
    RAPIDOCR = "rapidocr"


class PipelineOptions(BaseModel):
    """Base pipeline options."""

    create_legacy_output: bool = (
        True  # This default will be set to False on a future version of docling
    )
    document_timeout: Optional[float] = None
    accelerator_options: AcceleratorOptions = AcceleratorOptions()


class PdfPipelineOptions(PipelineOptions):
    """Options for the PDF pipeline."""

    artifacts_path: Optional[Union[Path, str]] = None
    do_table_structure: bool = True  # True: perform table structure extraction
    do_ocr: bool = True  # True: perform OCR, replace programmatic PDF text

    table_structure_options: TableStructureOptions = TableStructureOptions()
    ocr_options: Union[
        EasyOcrOptions,
        TesseractCliOcrOptions,
        TesseractOcrOptions,
        OcrMacOptions,
        RapidOcrOptions,
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
