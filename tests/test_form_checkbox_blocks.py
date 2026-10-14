# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""A checkbox the layout boxed together with its label is keyed by that label."""

from unittest.mock import MagicMock

import pytest
from docling_core.types.doc import BoundingBox, DocItemLabel, Size
from docling_core.types.doc.items.form import FieldItem
from docling_core.types.doc.page import BoundingRectangle, PdfWidget, TextCell

from docling.datamodel.base_models import Cluster, LayoutPrediction, Page

from .test_form_extraction import _materialize

# Tall enough for a note, a caption and three rows of PJ-1 page 4.
PAGE_HEIGHT = 120


def _block(
    cluster_id: int,
    label: DocItemLabel,
    bbox: BoundingBox,
    *lines: tuple[int, str, BoundingBox],
) -> Cluster:
    cells = [
        TextCell(
            index=index,
            rect=BoundingRectangle.from_bounding_box(box),
            text=text,
            orig=text,
            from_ocr=False,
        )
        for index, text, box in lines
    ]
    return Cluster(id=cluster_id, label=label, bbox=bbox, cells=cells)


def _checkbox(index: int, bbox: BoundingBox) -> PdfWidget:
    return PdfWidget(
        index=index,
        rect=BoundingRectangle.from_bounding_box(
            bbox.to_bottom_left_origin(page_height=PAGE_HEIGHT)
        ),
        widget_text="/Off",
        widget_field_type="/Btn",
        widget_appearance_state="/Off",
    )


def _page(clusters: list[Cluster], widgets) -> Page:
    page = Page(page_no=1, size=Size(width=595, height=PAGE_HEIGHT))
    page.parsed_page = MagicMock(widgets=widgets, hyperlinks=[])
    page.predictions.layout = LayoutPrediction(clusters=clusters)
    return page


def test_checkbox_in_its_label_block_is_keyed_by_the_whole_block() -> None:
    # PJ-1 page 4: a "Fotocópias de:" caption under a note, over rows of a
    # drawn square and a paragraph. The layout boxes each row as one
    # unselected checkbox, square included. The search would key every box
    # by the caption, which sits closer than the paragraph on the box's
    # right; each box is keyed by its own paragraph instead, which hosts the
    # item in place and is not emitted a second time.
    note = "Devem ser apresentados os documentos do requerente."
    note_bbox = BoundingBox(l=56.7, t=2.4, r=495.8, b=9.2)
    caption_bbox = BoundingBox(l=56.7, t=19.5, r=115.5, b=26.3)
    above = [
        _block(1, DocItemLabel.TEXT, note_bbox, (0, note, note_bbox)),
        _block(
            2,
            DocItemLabel.SECTION_HEADER,
            caption_bbox,
            (1, "Fotocópias de:", caption_bbox),
        ),
    ]
    rows = [
        _block(
            3,
            DocItemLabel.CHECKBOX_UNSELECTED,
            BoundingBox(l=55.5, t=32.4, r=538.7, b=64.5),
            (2, "Bilhete de identidade", BoundingBox(l=73.7, t=37.9, r=538.6, b=44.8)),
            (3, "do requerente e demais", BoundingBox(l=73.7, t=47.5, r=538.6, b=54.4)),
            (4, "pessoas.", BoundingBox(l=73.7, t=57.1, r=165.3, b=64.0)),
        ),
        _block(
            4,
            DocItemLabel.CHECKBOX_UNSELECTED,
            BoundingBox(l=55.2, t=67.9, r=513.3, b=80.7),
            (5, "Recibos de vencimento.", BoundingBox(l=73.7, t=73.2, r=513.3, b=80.1)),
        ),
        _block(
            5,
            DocItemLabel.CHECKBOX_UNSELECTED,
            BoundingBox(l=55.4, t=84.7, r=538.9, b=106.7),
            (6, "Declarações de IVA", BoundingBox(l=73.7, t=90.2, r=538.6, b=97.1)),
            (7, "dos dois trimestres.", BoundingBox(l=73.7, t=99.8, r=292.1, b=106.7)),
        ),
    ]
    widgets = [
        _checkbox(0, BoundingBox(l=58.8, t=34.8, r=66.8, b=42.8)),
        _checkbox(1, BoundingBox(l=58.8, t=70.2, r=66.8, b=78.2)),
        _checkbox(2, BoundingBox(l=58.8, t=87.2, r=66.8, b=95.2)),
    ]
    page = _page([*above, *rows], widgets)
    paragraphs = [" ".join(cell.text for cell in row.cells) for row in rows]

    doc = _materialize(page)

    assert [
        (region.source_container_id, [item.key_text for item in region.items])
        for region in page.predictions.field_regions
    ] == [(row.id, [text]) for row, text in zip(rows, paragraphs)]
    order = []
    for item, _ in doc.iterate_items(with_groups=False):
        if isinstance(item, FieldItem):
            order.append(item.children[0].resolve(doc).text)
        elif item.label not in {DocItemLabel.FIELD_KEY, DocItemLabel.FIELD_VALUE}:
            order.append(item.text)  # the boxes' own checkbox items are empty
    assert [text for text in order if text] == [note, "Fotocópias de:", *paragraphs]


def test_two_checkboxes_in_one_block_are_left_to_the_search() -> None:
    # A Yes/No pair the layout boxed as one checkbox block: the block's text
    # keys neither box as a whole; each box reads its own option key.
    block = _block(
        1,
        DocItemLabel.CHECKBOX_UNSELECTED,
        BoundingBox(l=10, t=10, r=90, b=30),
        (0, "Sim", BoundingBox(l=24, t=11, r=40, b=19)),
        (1, "Não", BoundingBox(l=24, t=21, r=40, b=29)),
    )
    widgets = [
        _checkbox(0, BoundingBox(l=12, t=11, r=20, b=19)),
        _checkbox(1, BoundingBox(l=12, t=21, r=20, b=29)),
    ]
    page = _page([block], widgets)

    _materialize(page)

    assert [
        item.key_text
        for region in page.predictions.field_regions
        for item in region.items
    ] == ["Sim", "Não"]


def _text_field(index: int, bbox: BoundingBox) -> PdfWidget:
    return PdfWidget(
        index=index,
        rect=BoundingRectangle.from_bounding_box(
            bbox.to_bottom_left_origin(page_height=PAGE_HEIGHT)
        ),
        widget_text="",
        widget_field_type="/Tx",
    )


def _keys(page: Page) -> list[str]:
    return [
        item.key_text
        for region in page.predictions.field_regions
        for item in region.items
    ]


def test_hosted_checkbox_key_is_located_by_its_text() -> None:
    # The block boxes the drawn square with its label, but the square is the
    # value's place: the key's location covers the label's text only.
    text_bbox = BoundingBox(l=73.7, t=37.9, r=300.0, b=44.8)
    block = _block(
        1,
        DocItemLabel.CHECKBOX_UNSELECTED,
        BoundingBox(l=55.5, t=32.4, r=300.0, b=46.0),
        (0, "Recibos de vencimento.", text_bbox),
    )
    page = _page([block], [_checkbox(0, BoundingBox(l=58.8, t=34.8, r=66.8, b=42.8))])

    doc = _materialize(page)

    (item,) = doc.field_items
    key = item.children[0].resolve(doc)
    assert key.text == "Recibos de vencimento."
    box = key.prov[0].bbox.to_top_left_origin(PAGE_HEIGHT)
    assert (box.l, box.t, box.r, box.b) == pytest.approx(
        (text_bbox.l, text_bbox.t, text_bbox.r, text_bbox.b)
    )


def test_block_with_no_letters_is_left_to_the_search() -> None:
    # A column of answer boxes printed after leader dots, which the layout
    # boxes as a checkbox block: the dots are no key, the column header is.
    header = "Grado igual o superior al 65%"
    header_bbox = BoundingBox(l=60, t=10, r=150, b=18)
    dots_bbox = BoundingBox(l=60, t=26, r=135, b=34)
    page = _page(
        [
            _block(1, DocItemLabel.TEXT, header_bbox, (0, header, header_bbox)),
            _block(
                2,
                DocItemLabel.CHECKBOX_UNSELECTED,
                BoundingBox(l=60, t=25, r=150, b=35),
                (1, "........................", dots_bbox),
            ),
        ],
        [_checkbox(0, BoundingBox(l=139, t=26, r=148, b=34))],
    )

    _materialize(page)

    assert _keys(page) == [header]


def test_block_label_also_keys_a_field_of_its_row() -> None:
    # "VISA Office" labels the checkbox in its block and the box on the same
    # row: the block's text keys the checkbox without taking the label from
    # the row's other field.
    label_bbox = BoundingBox(l=24, t=21, r=68, b=29)
    page = _page(
        [
            _block(
                1,
                DocItemLabel.CHECKBOX_UNSELECTED,
                BoundingBox(l=10, t=20, r=70, b=30),
                (0, "VISA Office", label_bbox),
            )
        ],
        [
            _checkbox(0, BoundingBox(l=12, t=21, r=20, b=29)),
            _text_field(1, BoundingBox(l=80, t=20, r=200, b=30)),
        ],
    )

    doc = _materialize(page)

    assert _keys(page) == ["VISA Office", "VISA Office"]
    assert all(item.label == DocItemLabel.FIELD_KEY for item in doc.texts if item.text)


def test_group_prompt_stays_when_one_option_is_keyed_by_its_block() -> None:
    # "3. SEX" asks a question answered by two checkboxes. MALE is boxed as a
    # checkbox block, FEMALE is plain text further right than an adjacent
    # option key. The question stays the group's prompt, so it does not key
    # FEMALE although it sits closer.
    prompt_bbox = BoundingBox(l=30, t=10, r=60, b=18)
    female_bbox = BoundingBox(l=55, t=28, r=85, b=36)
    male_bbox = BoundingBox(l=55, t=41, r=75, b=49)
    page = _page(
        [
            _block(1, DocItemLabel.TEXT, prompt_bbox, (0, "3. SEX", prompt_bbox)),
            _block(2, DocItemLabel.TEXT, female_bbox, (1, "FEMALE", female_bbox)),
            _block(
                3,
                DocItemLabel.CHECKBOX_UNSELECTED,
                BoundingBox(l=31, t=39, r=80, b=50),
                (2, "MALE", male_bbox),
            ),
        ],
        [
            _checkbox(0, BoundingBox(l=32, t=27, r=41, b=36)),
            _checkbox(1, BoundingBox(l=32, t=40, r=41, b=49)),
        ],
    )

    _materialize(page)

    keyed = {
        item.values[0].bbox.t: item.key_text
        for region in page.predictions.field_regions
        for item in region.items
    }
    assert keyed == {27: "FEMALE", 40: "MALE"}


def test_block_a_little_short_of_its_checkbox_still_keys_it() -> None:
    # The layout's block ends 0.1 pt above the drawn square's bottom; the
    # square is still the block's checkbox, not left to the caption above.
    caption_bbox = BoundingBox(l=56.7, t=19.5, r=115.5, b=26.3)
    text_bbox = BoundingBox(l=76.0, t=36.0, r=300.0, b=42.9)
    page = _page(
        [
            _block(
                1,
                DocItemLabel.SECTION_HEADER,
                caption_bbox,
                (0, "Fotocópias de:", caption_bbox),
            ),
            _block(
                2,
                DocItemLabel.CHECKBOX_UNSELECTED,
                BoundingBox(l=55.5, t=33.0, r=300.0, b=42.7),
                (1, "Recibos de vencimento.", text_bbox),
            ),
        ],
        [_checkbox(0, BoundingBox(l=58.8, t=34.8, r=66.8, b=42.8))],
    )

    _materialize(page)

    assert _keys(page) == ["Recibos de vencimento."]
