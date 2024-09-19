from enum import Enum, auto

from pydantic import BaseModel


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


class PipelineOptions(BaseModel):
    do_table_structure: bool = True  # True: perform table structure extraction
    do_ocr: bool = True  # True: perform OCR, replace programmatic PDF text

    table_structure_options: TableStructureOptions = TableStructureOptions()
