# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Mark superscript and subscript text in documents converted from PDF.

A text item holding such text becomes an inline group of runs with ``formatting.script``,
as the Word backend produces.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
from docling_core.types.doc import (
    BoundingBox,
    CoordOrigin,
    DocItemLabel,
    DoclingDocument,
    ProvenanceItem,
)
from docling_core.types.doc.document import (
    Formatting,
    InlineGroup,
    ListItem,
    NodeItem,
    Script,
    TextItem,
)

from docling.datamodel.document import ConversionResult
from docling.datamodel.pipeline_options import ScriptPositionOptions
from docling.utils.pdf_char_geometry import (
    PdfChar,
    PdfPageChars,
    open_pdf,
    pypdfium2_available,
    read_page_chars,
)
from docling.utils.profiling import ProfilingScope, TimeRecorder
from docling.utils.script_position import (
    ScriptRun,
    script_positions,
    script_runs,
)

_log = logging.getLogger(__name__)

# List items are handled too: they keep their item and get the runs as a child.
_TEXT_LABELS = frozenset(
    {DocItemLabel.TEXT, DocItemLabel.PARAGRAPH, DocItemLabel.FOOTNOTE}
)
# Slack (points) when testing whether a character's centre lies in an item's box.
_BOX_TOLERANCE = 0.5


class _Page:
    """A page's characters, with their centres in Docling's page frame."""

    def __init__(self, page: PdfPageChars):
        self.chars = page.chars
        centres = []
        for char in page.chars:
            left, bottom, right, top = page.to_display_frame(
                (char.left, char.bottom, char.right, char.top)
            )
            centres.append(((left + right) / 2, (bottom + top) / 2))
        self.centres = np.array(centres, dtype=float).reshape(-1, 2)
        self.page = page

    def indexes_in(self, box: BoundingBox) -> list[int]:
        """Return the characters whose centre is in a bottom-left-origin box."""
        if not len(self.centres):
            return []
        x, y = self.centres[:, 0], self.centres[:, 1]
        inside = (
            (x >= box.l - _BOX_TOLERANCE)
            & (x <= box.r + _BOX_TOLERANCE)
            & (y >= box.b - _BOX_TOLERANCE)
            & (y <= box.t + _BOX_TOLERANCE)
        )
        return np.flatnonzero(inside).tolist()

    def display_box(self, indexes: list[int]) -> BoundingBox:
        boxes = [
            self.page.to_display_frame((c.left, c.bottom, c.right, c.top))
            for c in (self.chars[i] for i in indexes)
        ]
        return BoundingBox(
            l=min(b[0] for b in boxes),
            b=min(b[1] for b in boxes),
            r=max(b[2] for b in boxes),
            t=max(b[3] for b in boxes),
            coord_origin=CoordOrigin.BOTTOMLEFT,
        )


class ScriptPositionModel:
    def __init__(self, options: ScriptPositionOptions):
        self.options = options

    def __call__(self, conv_res: ConversionResult) -> DoclingDocument:
        document = conv_res.document
        if not self.options.enabled:
            return document
        backend = conv_res.input._backend
        source = getattr(backend, "path_or_stream", None)
        if source is None:
            return document
        if not pypdfium2_available():
            _log.warning(
                "Superscript and subscript recovery needs pypdfium2, which is not "
                "installed; skipping it."
            )
            return document

        password = getattr(getattr(backend, "options", None), "password", None)
        with TimeRecorder(conv_res, "script_position", scope=ProfilingScope.DOCUMENT):
            try:
                with open_pdf(
                    source,
                    password.get_secret_value() if password else None,
                ) as pdf:
                    pages: dict[int, Optional[_Page]] = {}

                    def page_for(page_no: int) -> Optional[_Page]:
                        if page_no not in pages:
                            try:
                                pages[page_no] = _Page(
                                    read_page_chars(pdf, page_no - 1)
                                )
                            except Exception as exc:
                                _log.debug(
                                    f"Cannot read characters of page {page_no}: {exc}"
                                )
                                pages[page_no] = None
                        return pages[page_no]

                    self.mark_scripts(document, page_for)
            except Exception as exc:
                _log.warning(f"Superscript and subscript recovery failed: {exc}")
        return document

    def mark_scripts(self, document: DoclingDocument, page_for) -> None:
        """Rewrite the text items holding superscript or subscript text.

        ``page_for`` returns the characters of a 1-based page, or None.
        """
        referenced = {
            ref.cref
            for item in [*document.tables, *document.pictures]
            for ref in [*item.captions, *item.footnotes, *item.references]
        }
        replaced: list[NodeItem] = []
        try:
            for item, _ in list(document.iterate_items(with_groups=False)):
                if not isinstance(item, TextItem) or not item.prov or not item.text:
                    continue
                if item.self_ref in referenced or isinstance(
                    item.parent.resolve(document) if item.parent else None,
                    InlineGroup,
                ):
                    continue
                is_list_item = isinstance(item, ListItem)
                if not is_list_item and item.label not in _TEXT_LABELS:
                    continue

                located = self._item_chars(document, item, page_for)
                if located is None:
                    continue
                chars, owners = located
                runs = script_runs(item.text, chars, script_positions(chars))
                if runs is None:
                    continue

                self._write_runs(document, item, runs, owners, page_for)
                if not is_list_item:
                    replaced.append(item)
        finally:
            # An item already rewritten as a group must not stay beside it.
            if replaced:
                document.delete_items(node_items=replaced)

    @staticmethod
    def _item_chars(document: DoclingDocument, item: TextItem, page_for):
        """Return the PDF characters in the item's boxes, with (page, index) of each."""
        chars: list[PdfChar] = []
        owners: list[tuple[int, int]] = []
        seen: set[tuple[int, int]] = set()
        for prov in item.prov:
            page = page_for(prov.page_no)
            doc_page = document.pages.get(prov.page_no)
            if page is None or doc_page is None:
                continue
            box = prov.bbox.to_bottom_left_origin(doc_page.size.height)
            for index in page.indexes_in(box):
                if (prov.page_no, index) in seen:
                    continue
                seen.add((prov.page_no, index))
                chars.append(page.chars[index])
                owners.append((prov.page_no, index))
        if not any(not c.text.isspace() for c in chars):
            return None
        return chars, owners

    @staticmethod
    def _write_runs(
        document: DoclingDocument,
        item: TextItem,
        runs: list[ScriptRun],
        owners: list[tuple[int, int]],
        page_for,
    ) -> None:
        if isinstance(item, ListItem):
            # As in the Word backend, the list item keeps its marker and holds the runs.
            if item.children:
                group = document.insert_inline_group(
                    sibling=item.children[0].resolve(document),
                    content_layer=item.content_layer,
                    after=False,
                )
            else:
                group = document.add_inline_group(
                    parent=item, content_layer=item.content_layer
                )
            label = DocItemLabel.TEXT
            item.text = ""
            item.orig = ""
        else:
            group = document.insert_inline_group(
                sibling=item, content_layer=item.content_layer, after=False
            )
            label = item.label

        base = item.formatting
        for run in runs:
            formatting = None
            if run.script != Script.BASELINE or base is not None:
                formatting = (base or Formatting()).model_copy(
                    update={"script": run.script}
                )
            document.add_text(
                label=label,
                text=run.text,
                orig=run.text,
                prov=_run_prov(item, run, owners, page_for),
                parent=group,
                formatting=formatting,
                hyperlink=item.hyperlink,
                content_layer=item.content_layer,
            )


def _run_prov(
    item: TextItem, run: ScriptRun, owners: list[tuple[int, int]], page_for
) -> ProvenanceItem:
    """Box the run's characters, falling back to the item's first box."""
    hits = [owners[k] for k in run.chars]
    if hits:
        page_no = hits[0][0]
        page = page_for(page_no)
        if page is not None:
            return ProvenanceItem(
                page_no=page_no,
                bbox=page.display_box([i for p, i in hits if p == page_no]),
                charspan=(0, len(run.text)),
            )
    prov = item.prov[0]
    return ProvenanceItem(
        page_no=prov.page_no, bbox=prov.bbox, charspan=(0, len(run.text))
    )
