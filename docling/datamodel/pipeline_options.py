from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import AnyUrl, BaseModel, ConfigDict, Field


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
    bitmap_area_threshold: float = (
        0.05  # percentage of the area for a bitmap to processed with OCR
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


class PicDescBaseOptions(BaseModel):
    kind: str
    batch_size: int = 8
    scale: float = 2

    bitmap_area_threshold: float = (
        0.2  # percentage of the area for a bitmap to processed with the models
    )


class PicDescApiOptions(PicDescBaseOptions):
    kind: Literal["api"] = "api"

    url: AnyUrl = AnyUrl("")
    headers: Dict[str, str] = {}
    params: Dict[str, Any] = {}
    timeout: float = 20

    llm_prompt: str = ""
    provenance: str = ""


class PicDescVllmOptions(PicDescBaseOptions):
    kind: Literal["vllm"] = "vllm"

    # For more example parameters see https://docs.vllm.ai/en/latest/getting_started/examples/offline_inference_vision_language.html

    # Parameters for LLaVA-1.6/LLaVA-NeXT
    llm_name: str = "llava-hf/llava-v1.6-mistral-7b-hf"
    llm_prompt: str = "[INST] <image>\nDescribe the image in details. [/INST]"
    llm_extra: Dict[str, Any] = dict(max_model_len=8192)

    # Parameters for Phi-3-Vision
    # llm_name: str = "microsoft/Phi-3-vision-128k-instruct"
    # llm_prompt: str = "<|user|>\n<|image_1|>\nDescribe the image in details.<|end|>\n<|assistant|>\n"
    # llm_extra: Dict[str, Any] = dict(max_num_seqs=5, trust_remote_code=True)

    sampling_params: Dict[str, Any] = dict(max_tokens=64, seed=42)


class PipelineOptions(BaseModel):
    create_legacy_output: bool = (
        True  # This defautl will be set to False on a future version of docling
    )


class PdfPipelineOptions(PipelineOptions):
    artifacts_path: Optional[Union[Path, str]] = None
    do_table_structure: bool = True  # True: perform table structure extraction
    do_ocr: bool = True  # True: perform OCR, replace programmatic PDF text
    do_picture_description: bool = False

    table_structure_options: TableStructureOptions = TableStructureOptions()
    ocr_options: Union[EasyOcrOptions, TesseractCliOcrOptions, TesseractOcrOptions] = (
        Field(EasyOcrOptions(), discriminator="kind")
    )
    picture_description_options: Annotated[
        Union[PicDescApiOptions, PicDescVllmOptions], Field(discriminator="kind")
    ] = PicDescApiOptions()  # TODO: needs defaults or optional

    images_scale: float = 1.0
    generate_page_images: bool = False
    generate_picture_images: bool = False
    generate_table_images: bool = False
