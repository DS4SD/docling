# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""`page_bitmap_area_threshold` OCRs only the pages that bitmaps mostly cover.

It restores the "OCR only scanned pages" use case of the `bitmap_area_threshold`
removed with the introduction of `OcrMode` (#4834). A page below the threshold
skips OCR, so it must keep its native text, also in `FULL_PAGE` mode, where OCR
cells normally replace the native cells and their extraction is skipped.
"""

from collections.abc import Iterable
from pathlib import Path
from types import SimpleNamespace

import pytest
from docling_core.types.doc import BoundingBox

from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.accelerator_options import AcceleratorOptions
from docling.datamodel.base_models import ConfidenceReport, InputFormat, Page
from docling.datamodel.document import ConversionResult, InputDocument
from docling.datamodel.pipeline_options import (
    EasyOcrOptions,
    OcrMode,
    OcrOptions,
    PdfPipelineOptions,
    RapidOcrOptions,
    TesseractOcrOptions,
)
from docling.models.base_ocr_model import BaseOcrModel
from docling.models.stages.page_preprocessing.page_preprocessing_model import (
    resolve_skip_cell_extraction,
)

OCR_OPTION_CLASSES = [EasyOcrOptions, RapidOcrOptions, TesseractOcrOptions]

# First pages: a scan (bitmaps cover all of it) and a programmatic page whose
# pictures cover about 15% of it.
SCANNED_PDF = Path("tests/data/ocr/sources/ocr_test.pdf")
PROGRAMMATIC_PDF = Path("tests/data/pdf/sources/picture_classification.pdf")


class _OcrRectsOnlyModel(BaseOcrModel):
    """Minimal concrete `BaseOcrModel`: only the page selection is under test."""

    def __call__(
        self, conv_res: ConversionResult, page_batch: Iterable[Page]
    ) -> Iterable[Page]:
        raise NotImplementedError

    @classmethod
    def get_options_type(cls) -> type[OcrOptions]:
        return OcrOptions


def _model(mode: OcrMode, threshold: float | None) -> _OcrRectsOnlyModel:
    return _OcrRectsOnlyModel(
        enabled=True,
        artifacts_path=None,
        options=OcrOptions(
            kind="test", lang=["en"], mode=mode, page_bitmap_area_threshold=threshold
        ),
        accelerator_options=AcceleratorOptions(),
    )


def _first_page(pdf: Path) -> Page:
    in_doc = InputDocument(
        path_or_stream=pdf, format=InputFormat.PDF, backend=PyPdfiumDocumentBackend
    )
    page = Page(page_no=1)
    page._backend = in_doc._backend.load_page(0)
    page.size = page._backend.get_size()
    page.parsed_page = page._backend.get_segmented_page()
    return page


def _ocr_rects(pdf: Path, threshold: float | None) -> list[BoundingBox]:
    return _model(OcrMode.FULL_PAGE, threshold).get_ocr_rects(_first_page(pdf))


@pytest.mark.parametrize("options_cls", OCR_OPTION_CLASSES)
def test_removed_bitmap_area_threshold_is_accepted_as_deprecated(options_cls):
    """Configurations written before `OcrMode` must not fail validation."""
    with pytest.deprecated_call(match="page_bitmap_area_threshold"):
        options = options_cls(bitmap_area_threshold=0.97)

    assert options.page_bitmap_area_threshold == 0.97


def test_explicit_threshold_wins_over_the_deprecated_one():
    with pytest.deprecated_call():
        options = EasyOcrOptions(
            bitmap_area_threshold=0.05, page_bitmap_area_threshold=0.97
        )

    assert options.page_bitmap_area_threshold == 0.97


def test_scanned_page_is_ocred_above_the_threshold():
    assert len(_ocr_rects(SCANNED_PDF, threshold=0.97)) == 1


def test_programmatic_page_skips_ocr_below_the_threshold():
    assert _ocr_rects(PROGRAMMATIC_PDF, threshold=0.97) == []


def test_without_threshold_every_page_is_ocred():
    assert len(_ocr_rects(PROGRAMMATIC_PDF, threshold=None)) == 1


def test_full_page_ocr_keeps_the_native_text_of_a_skipped_page():
    """With no OCR cells, a skipped page would otherwise lose all its text."""
    page = _first_page(PROGRAMMATIC_PDF)
    native_text = [cell.text for cell in page.cells]
    assert native_text

    model = _model(OcrMode.FULL_PAGE, threshold=0.97)
    model.post_process_cells([], page, SimpleNamespace(confidence=ConfidenceReport()))

    assert [cell.text for cell in page.cells] == native_text


def test_full_page_ocr_with_threshold_extracts_the_native_text():
    """The pages below the threshold need the native cells that FULL_PAGE skips."""
    options = PdfPipelineOptions(
        do_ocr=True,
        ocr_options=EasyOcrOptions(
            mode=OcrMode.FULL_PAGE, page_bitmap_area_threshold=0.97
        ),
    )

    assert resolve_skip_cell_extraction(options) is False
