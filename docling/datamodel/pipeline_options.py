import warnings
from enum import Enum, auto
from pathlib import Path
from typing import Annotated, Optional, Self, Union

from pydantic import BaseModel, Field, model_validator


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


class PipelineOptions(BaseModel): ...


class PdfPipelineOptions(PipelineOptions):
    artifacts_path: Optional[Union[Path, str]] = None
    do_table_structure: bool = True  # True: perform table structure extraction
    do_ocr: bool = True  # True: perform OCR, replace programmatic PDF text

    table_structure_options: TableStructureOptions = TableStructureOptions()

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
