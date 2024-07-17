import logging
import re
from typing import Iterable, List

from docling.datamodel.base_models import (
    AssembledUnit,
    FigureElement,
    Page,
    PageElement,
    TableElement,
    TextElement,
)
from docling.models.layout_model import LayoutModel

_log = logging.getLogger(__name__)


class PageAssembleModel:
    def __init__(self, config):
        self.config = config

    def sanitize_text(self, lines):
        if len(lines) <= 1:
            return " ".join(lines)

        for ix, line in enumerate(lines[1:]):
            prev_line = lines[ix]

            if prev_line.endswith("-"):
                prev_words = re.findall(r"\b[\w]+\b", prev_line)
                line_words = re.findall(r"\b[\w]+\b", line)

                if (
                    len(prev_words)
                    and len(line_words)
                    and prev_words[-1].isalnum()
                    and line_words[0].isalnum()
                ):
                    lines[ix] = prev_line[:-1]
            else:
                lines[ix] += " "

        sanitized_text = "".join(lines)

        return sanitized_text.strip()  # Strip any leading or trailing whitespace

    def __call__(self, page_batch: Iterable[Page]) -> Iterable[Page]:
        for page in page_batch:
            # assembles some JSON output page by page.

            elements: List[PageElement] = []
            headers: List[PageElement] = []
            body: List[PageElement] = []

            for cluster in page.predictions.layout.clusters:
                # _log.info("Cluster label seen:", cluster.label)
                if cluster.label in LayoutModel.TEXT_ELEM_LABELS:

                    textlines = [
                        cell.text.replace("\x02", "-").strip()
                        for cell in cluster.cells
                        if len(cell.text.strip()) > 0
                    ]
                    text = self.sanitize_text(textlines)
                    text_el = TextElement(
                        label=cluster.label,
                        id=cluster.id,
                        text=text,
                        page_no=page.page_no,
                        cluster=cluster,
                    )
                    elements.append(text_el)

                    if cluster.label in LayoutModel.PAGE_HEADER_LABELS:
                        headers.append(text_el)
                    else:
                        body.append(text_el)
                elif cluster.label == LayoutModel.TABLE_LABEL:
                    tbl = None
                    if page.predictions.tablestructure:
                        tbl = page.predictions.tablestructure.table_map.get(
                            cluster.id, None
                        )
                    if (
                        not tbl
                    ):  # fallback: add table without structure, if it isn't present
                        tbl = TableElement(
                            label=cluster.label,
                            id=cluster.id,
                            text="",
                            otsl_seq=[],
                            table_cells=[],
                            cluster=cluster,
                            page_no=page.page_no,
                        )

                    elements.append(tbl)
                    body.append(tbl)
                elif cluster.label == LayoutModel.FIGURE_LABEL:
                    fig = None
                    if page.predictions.figures_classification:
                        fig = page.predictions.figures_classification.figure_map.get(
                            cluster.id, None
                        )
                    if (
                        not fig
                    ):  # fallback: add figure without classification, if it isn't present
                        fig = FigureElement(
                            label=cluster.label,
                            id=cluster.id,
                            text="",
                            data=None,
                            cluster=cluster,
                            page_no=page.page_no,
                        )
                    elements.append(fig)
                    body.append(fig)
                elif cluster.label == LayoutModel.FORMULA_LABEL:
                    equation = None
                    if page.predictions.equations_prediction:
                        equation = (
                            page.predictions.equations_prediction.equation_map.get(
                                cluster.id, None
                            )
                        )
                    if not equation:  # fallback: add empty formula, if it isn't present
                        text = self.sanitize_text(
                            [
                                cell.text.replace("\x02", "-").strip()
                                for cell in cluster.cells
                                if len(cell.text.strip()) > 0
                            ]
                        )
                        equation = TextElement(
                            label=cluster.label,
                            id=cluster.id,
                            cluster=cluster,
                            page_no=page.page_no,
                            text=text,
                        )
                    elements.append(equation)
                    body.append(equation)

            page.assembled = AssembledUnit(
                elements=elements, headers=headers, body=body
            )

            yield page
