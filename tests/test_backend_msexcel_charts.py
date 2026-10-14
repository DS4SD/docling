# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Tests for Excel combination charts: several plots in one chart."""

import datetime
from pathlib import Path
from typing import Any

import pytest
from docling_core.types.doc import PictureClassificationLabel, PictureItem
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference

from docling.backend.msexcel_backend import MsExcelDocumentBackend
from docling.datamodel.backend_options import MsExcelBackendOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import InputDocument

from .test_backend_msexcel import get_converter

_MONTHS = [datetime.datetime(2012, month, 1) for month in range(1, 13)]
_BARS = {
    "East": (85, 34, 100, 80, 116, 88, 71, 90, 121, 110, 101, 81),
    "West": (94, 72, 62, 91, 99, 70, 71, 46, 91, 57, 32, 157),
    "North": (91, 59, 85, 67, 130, 66, 51, 40, 62, 61, 61, 52),
    "South": (71, 110, 101, 28, 39, 52, 48, 125, 43, 122, 60, 63),
}
_LINES = {
    "Margin": tuple(
        n / 1000 for n in (126, 74, 110, 92, 86, 89, 77, 40, 101, 62, 81, 62)
    ),
    "Target": tuple(
        n / 1000 for n in (91, 75, 94, 72, 103, 75, 66, 81, 85, 94, 69, 95)
    ),
}


def _save_combo_chart_workbook(path: Path) -> None:
    """Save a workbook whose chart draws columns and lines on a second axis.

    This is how Excel stores a "Clustered Column - Line on Secondary Axis"
    chart: a ``c:barChart`` with the four region series, then a
    ``c:lineChart`` with the two ratio series on a secondary value axis. Both
    plots share the date categories in column A. The category axis is titled
    "Region Position" and the primary value axis "Bar Sales".
    """
    workbook = Workbook()
    sheet = workbook.worksheets[0]
    sheet.append(["Month", *_BARS, *_LINES])
    for row, month in enumerate(_MONTHS):
        sheet.append(
            [month, *(v[row] for v in _BARS.values())]
            + [v[row] for v in _LINES.values()]
        )
    last_row = 1 + len(_MONTHS)
    categories = Reference(sheet, min_col=1, min_row=2, max_row=last_row)

    bars = BarChart()
    bars.title = "Sales and Margin"
    bars.add_data(
        Reference(sheet, min_col=2, max_col=5, min_row=1, max_row=last_row),
        titles_from_data=True,
    )
    bars.set_categories(categories)
    bars.x_axis.title = "Region Position"
    bars.y_axis.title = "Bar Sales"

    lines = LineChart()
    lines.add_data(
        Reference(sheet, min_col=6, max_col=7, min_row=1, max_row=last_row),
        titles_from_data=True,
    )
    lines.set_categories(categories)
    lines.y_axis.axId = 200
    lines.y_axis.crosses = "max"

    bars += lines
    sheet.add_chart(bars, "J2")
    workbook.save(path)


def _only_chart(path: Path) -> PictureItem:
    doc = get_converter().convert(path).document
    pictures = list(doc.pictures)
    assert len(pictures) == 1
    return pictures[0]


def _grid(picture: PictureItem) -> list[list[str]]:
    assert picture.meta is not None and picture.meta.tabular_chart is not None
    return [
        [cell.text for cell in row]
        for row in picture.meta.tabular_chart.chart_data.grid
    ]


def _labels(picture: PictureItem) -> list[str]:
    assert picture.meta is not None and picture.meta.classification is not None
    return [p.class_name for p in picture.meta.classification.predictions]


def test_combo_chart_lists_each_plot_type_and_keeps_all_series(tmp_path: Path):
    """A column + line chart keeps its line series and is classified as both.

    openpyxl gives the first plot as the chart, so before only the four column
    series were read and the chart was a bar chart only. The main prediction
    stays the column plot, so serializers that read only the main prediction
    still treat the picture as a bar chart.
    """
    path = tmp_path / "combo_chart.xlsx"
    _save_combo_chart_workbook(path)

    picture = _only_chart(path)

    assert _labels(picture) == [
        PictureClassificationLabel.BAR_CHART.value,
        PictureClassificationLabel.LINE_CHART.value,
    ]
    grid = _grid(picture)
    assert grid[0][1:] == ["East", "West", "North", "South", "Margin", "Target"]
    assert grid[1][1:] == ["85", "94", "91", "71", "0.126", "0.091"]
    assert len(grid) == 1 + len(_MONTHS)


def test_date_categories_are_iso_dates(tmp_path: Path):
    """Date categories read as ISO 8601 dates, without a midnight time.

    openpyxl reads a date cell as a ``datetime``, which was written as
    ``2012-01-01 00:00:00``.
    """
    path = tmp_path / "combo_chart.xlsx"
    _save_combo_chart_workbook(path)

    grid = _grid(_only_chart(path))

    assert [row[0] for row in grid[1:]] == [
        month.date().isoformat() for month in _MONTHS
    ]


def test_category_axis_title_heads_the_category_column(tmp_path: Path):
    """The category axis title fills the top-left cell of the data table.

    That cell was always empty. The value axis title has no column to head,
    so it stays out.
    """
    path = tmp_path / "combo_chart.xlsx"
    _save_combo_chart_workbook(path)

    grid = _grid(_only_chart(path))

    assert grid[0] == ["Region Position", *_BARS, *_LINES]


def test_render_workbook_holds_the_data_of_every_plot(tmp_path: Path):
    """The workbook that LibreOffice renders holds the line series data too.

    The render workbook keeps every plot of the chart, but before only the
    data of the first plot was copied into it, so the line plot had no data.
    Only the workbook assembly is exercised, so this runs without LibreOffice.
    """
    path = tmp_path / "combo_chart.xlsx"
    _save_combo_chart_workbook(path)
    in_doc = InputDocument(
        path_or_stream=path,
        format=InputFormat.XLSX,
        filename=path.stem,
        backend=MsExcelDocumentBackend,
    )
    backend = MsExcelDocumentBackend(
        in_doc=in_doc,
        path_or_stream=path,
        options=MsExcelBackendOptions(render_chart_images=True),
    )
    source_sheet = backend.workbook.worksheets[0]
    chart = source_sheet._charts[0]

    standalone = backend._build_standalone_chart_workbook(chart)

    assert standalone is not None
    data_sheet = standalone[source_sheet.title]
    assert [data_sheet.cell(row=1, column=col).value for col in (6, 7)] == list(_LINES)
    assert data_sheet.cell(row=2, column=6).value == _LINES["Margin"][0]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (datetime.datetime(2012, 1, 1), "2012-01-01"),
        (datetime.datetime(2012, 1, 1, 12, 30), "2012-01-01T12:30:00"),
        (0.126, "0.126"),
    ],
)
def test_chart_cell_text(value: Any, expected: str):
    """A date keeps its time of day only when it has one; numbers stay as they are."""
    assert MsExcelDocumentBackend._chart_cell_text(value) == expected
