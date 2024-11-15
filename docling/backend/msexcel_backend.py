import logging
from io import BytesIO
from pathlib import Path
from typing import Set, Union

from lxml import etree
from openpyxl import load_workbook
from openpyxl.cell.cell import Cell

from docling.backend.abstract_backend import DeclarativeDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import InputDocument

_log = logging.getLogger(__name__)


class MsExcelDocumentBackend(DeclarativeDocumentBackend):

    def __init__(self, in_doc: "InputDocument", path_or_stream: Union[BytesIO, Path]):
        super().__init__(in_doc, path_or_stream)

        # Initialise the parents for the hierarchy
        self.max_levels = 10

        self.parents = {}  # type: ignore
        for i in range(-1, self.max_levels):
            self.parents[i] = None

        self.workbook = None
        try:
            if isinstance(self.path_or_stream, BytesIO):
                self.workbook = load_workbook(filename=self.path_or_stream)

            elif isinstance(self.path_or_stream, Path):
                self.workbook = load_workbook(filename=str(self.path_or_stream))

            self.valid = True
        except Exception as e:
            self.valid = False

            raise RuntimeError(
                f"MsPowerpointDocumentBackend could not load document with hash {self.document_hash}"
            ) from e

    def is_valid(self) -> bool:
        return self.valid

    @classmethod
    def supports_pagination(cls) -> bool:
        return True

    def unload(self):
        if isinstance(self.path_or_stream, BytesIO):
            self.path_or_stream.close()

        self.path_or_stream = None

    @classmethod
    def supported_formats(cls) -> Set[InputFormat]:
        return {InputFormat.EXCEL}

    def convert(self) -> DoclingDocument:
        # Parses the DOCX into a structured document model.

        origin = DocumentOrigin(
            filename=self.file.name or "file",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            binary_hash=self.document_hash,
        )

        if self.is_valid():
            return self.convert_workbook(doc)
        else:
            raise RuntimeError(
                f"Cannot convert doc with {self.document_hash} because the backend failed to init."
            )

        return DoclingDocument(name=self.file.stem or "file", origin=origin)

    def get_level(self) -> int:
        """Return the first None index."""
        for k, v in self.parents.items():
            if k >= 0 and v == None:
                return k
        return 0

    def convert_workbook(self) -> DoclingDocument:

        doc = DoclingDocument(name=self.file.stem or "file", origin=origin)

        # Iterate over all sheets
        for sheet_name in workbook.sheetnames:
            _log.info(f"Processing sheet: {sheet_name}")
            sheet = workbook[sheet_name]  # Access the sheet by name

            # level = self.get_level()

            self.parents[0] = doc.add_group(
                parent=None,  # self.parents[level-1],
                label=GroupLabel.SECTION,
                name=f"sheet: {sheet_name}",
            )

            self.convert_sheet(doc, sheet)

    def convert_sheet(self, doc: DoclingDocument, sheet):

        tables = self.find_data_tables(sheet)

        for excel_table in tables:

            table_data = TableData(
                num_rows=excel_table["num_rows"],
                num_cols=excel_table["num_cols"],
                table_cells=[],
            )

            for excel_cell in excel_table["data"]:
                cell = TableCell(
                    text=str(excel_cell.value),
                    row_span=excel_cell["row_span"],
                    col_span=excel_cell["col_span"],
                    start_row_offset_idx=excel_cell["row"],
                    end_row_offset_idx=excel_cell["row"] + excel_cell["row_span"],
                    start_col_offset_idx=excel_cell["col"],
                    end_col_offset_idx=excel_cell["col"] + excel_cell["col_span"],
                    col_header=False,  # col_header,
                    row_header=False,  # ((not col_header) and html_cell.name=='th')
                )
                data.table_cells.append(cell)

            doc.append_table(data=table_data, parent=self.parents[0])

    def find_data_tables(self, sheet):
        """
        Find all compact rectangular data tables in a sheet.
        """
        tables = []  # List to store found tables
        visited = set()  # Track already visited cells

        # Iterate over all cells in the sheet
        for ri, row in enumerate(sheet.iter_rows(values_only=False)):
            for rj, cell in enumerate(row):
                # Skip empty or already visited cells
                if cell.value is None or (ri, rj) in visited:
                    continue

                # If the cell starts a new table, find its bounds
                table_bounds, visited_cells = find_table_bounds(sheet, ri, rj, visited)
                visited.update(visited_cells)  # Mark these cells as visited
                tables.append(table_bounds)

        return tables

    def find_table_bounds(self, sheet, start_row, start_col, visited):
        """
        Determine the bounds of a compact rectangular table.
        Returns:
        - A dictionary with the bounds and data.
        - A set of visited cell coordinates.
        """
        max_row = start_row
        max_col = start_col

        # Expand downward to find the table's bottom boundary
        while (
            max_row < sheet.max_row - 1
            and sheet.cell(row=max_row + 2, column=start_col + 1).value is not None
        ):
            max_row += 1

        # Expand rightward to find the table's right boundary
        while (
            max_col < sheet.max_column - 1
            and sheet.cell(row=start_row + 1, column=max_col + 2).value is not None
        ):
            max_col += 1

        # Collect the data within the bounds
        data = []
        visited_cells = set()
        for ri in range(start_row, max_row + 1):
            row_data = []
            for rj in range(start_col, max_col + 1):

                cell = sheet.cell(row=ri + 1, column=rj + 1)  # 1-based indexing

                # Check if the cell belongs to a merged range
                row_span = 1
                col_span = 1
                for merged_range in sheet.merged_cells.ranges:
                    if (ri + 1, rj + 1) in merged_range:
                        # Calculate the spans
                        row_span = merged_range.max_row - merged_range.min_row + 1
                        col_span = merged_range.max_col - merged_range.min_col + 1
                        break

                # Register the cell with spans
                row_data.append(
                    {
                        "row": ri - start_row,
                        "col": rj - start_col,
                        "cell": cell,
                        "row_span": row_span,
                        "col_span": col_span,
                    }
                )

                # Mark all cells in the span as visited
                for span_row in range(ri, ri + row_span):
                    for span_col in range(rj, rj + col_span):
                        visited_cells.add((span_row, span_col))

            data.append(row_data)

        return {
            "beg_row": start_row,
            "beg_col": start_col,
            "end_row": max_row,
            "end_col": max_col,
            "num_rows": max_row - start_row,
            "num_cols": max_col - start_col,
            "data": data,
        }, visited_cells
