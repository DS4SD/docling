import random
from io import BytesIO
from pathlib import Path
from typing import Iterable, List, Optional, Union

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c
from PIL import Image, ImageDraw
from pypdfium2 import PdfPage

from docling.backend.abstract_backend import PdfDocumentBackend, PdfPageBackend
from docling.datamodel.base_models import BoundingBox, Cell, CoordOrigin, PageSize


class PyPdfiumPageBackend(PdfPageBackend):
    def __init__(self, page_obj: PdfPage):
        super().__init__(page_obj)
        self._ppage = page_obj
        self.text_page = None

    def get_bitmap_rects(self, scale: int = 1) -> Iterable[BoundingBox]:
        AREA_THRESHOLD = 32 * 32
        for obj in self._ppage.get_objects(filter=[pdfium_c.FPDF_PAGEOBJ_IMAGE]):
            pos = obj.get_pos()
            cropbox = BoundingBox.from_tuple(
                pos, origin=CoordOrigin.BOTTOMLEFT
            ).to_top_left_origin(page_height=self.get_size().height)

            if cropbox.area() > AREA_THRESHOLD:
                cropbox = cropbox.scaled(scale=scale)

                yield cropbox

    def get_text_in_rect(self, bbox: BoundingBox) -> str:
        if not self.text_page:
            self.text_page = self._ppage.get_textpage()

        if bbox.coord_origin != CoordOrigin.BOTTOMLEFT:
            bbox = bbox.to_bottom_left_origin(self.get_size().height)

        text_piece = self.text_page.get_text_bounded(*bbox.as_tuple())

        return text_piece

    def get_text_cells(self) -> Iterable[Cell]:
        if not self.text_page:
            self.text_page = self._ppage.get_textpage()

        cells = []
        cell_counter = 0

        page_size = self.get_size()

        for i in range(self.text_page.count_rects()):
            rect = self.text_page.get_rect(i)
            text_piece = self.text_page.get_text_bounded(*rect)
            x0, y0, x1, y1 = rect
            cells.append(
                Cell(
                    id=cell_counter,
                    text=text_piece,
                    bbox=BoundingBox(
                        l=x0, b=y0, r=x1, t=y1, coord_origin=CoordOrigin.BOTTOMLEFT
                    ).to_top_left_origin(page_size.height),
                )
            )
            cell_counter += 1

        # PyPdfium2 produces very fragmented cells, with sub-word level boundaries, in many PDFs.
        # The cell merging code below is to clean this up.
        def merge_horizontal_cells(
            cells: List[Cell],
            horizontal_threshold_factor: float = 1.0,
            vertical_threshold_factor: float = 0.5,
        ) -> List[Cell]:
            if not cells:
                return []

            def group_rows(cells: List[Cell]) -> List[List[Cell]]:
                rows = []
                current_row = [cells[0]]
                row_top = cells[0].bbox.t
                row_bottom = cells[0].bbox.b
                row_height = cells[0].bbox.height

                for cell in cells[1:]:
                    vertical_threshold = row_height * vertical_threshold_factor
                    if (
                        abs(cell.bbox.t - row_top) <= vertical_threshold
                        and abs(cell.bbox.b - row_bottom) <= vertical_threshold
                    ):
                        current_row.append(cell)
                        row_top = min(row_top, cell.bbox.t)
                        row_bottom = max(row_bottom, cell.bbox.b)
                        row_height = row_bottom - row_top
                    else:
                        rows.append(current_row)
                        current_row = [cell]
                        row_top = cell.bbox.t
                        row_bottom = cell.bbox.b
                        row_height = cell.bbox.height

                if current_row:
                    rows.append(current_row)

                return rows

            def merge_row(row: List[Cell]) -> List[Cell]:
                merged = []
                current_group = [row[0]]

                for cell in row[1:]:
                    prev_cell = current_group[-1]
                    avg_height = (prev_cell.bbox.height + cell.bbox.height) / 2
                    if (
                        cell.bbox.l - prev_cell.bbox.r
                        <= avg_height * horizontal_threshold_factor
                    ):
                        current_group.append(cell)
                    else:
                        merged.append(merge_group(current_group))
                        current_group = [cell]

                if current_group:
                    merged.append(merge_group(current_group))

                return merged

            def merge_group(group: List[Cell]) -> Cell:
                if len(group) == 1:
                    return group[0]

                merged_text = "".join(cell.text for cell in group)
                merged_bbox = BoundingBox(
                    l=min(cell.bbox.l for cell in group),
                    t=min(cell.bbox.t for cell in group),
                    r=max(cell.bbox.r for cell in group),
                    b=max(cell.bbox.b for cell in group),
                )
                return Cell(id=group[0].id, text=merged_text, bbox=merged_bbox)

            rows = group_rows(cells)
            merged_cells = [cell for row in rows for cell in merge_row(row)]

            for i, cell in enumerate(merged_cells, 1):
                cell.id = i

            return merged_cells

        def draw_clusters_and_cells():
            image = (
                self.get_page_image()
            )  # make new image to avoid drawing on the saved ones
            draw = ImageDraw.Draw(image)
            for c in cells:
                x0, y0, x1, y1 = c.bbox.as_tuple()
                cell_color = (
                    random.randint(30, 140),
                    random.randint(30, 140),
                    random.randint(30, 140),
                )
                draw.rectangle([(x0, y0), (x1, y1)], outline=cell_color)
            image.show()

        # before merge:
        # draw_clusters_and_cells()

        cells = merge_horizontal_cells(cells)

        # after merge:
        # draw_clusters_and_cells()

        return cells

    def get_page_image(
        self, scale: int = 1, cropbox: Optional[BoundingBox] = None
    ) -> Image.Image:

        page_size = self.get_size()

        if not cropbox:
            cropbox = BoundingBox(
                l=0,
                r=page_size.width,
                t=0,
                b=page_size.height,
                coord_origin=CoordOrigin.TOPLEFT,
            )
            padbox = BoundingBox(
                l=0, r=0, t=0, b=0, coord_origin=CoordOrigin.BOTTOMLEFT
            )
        else:
            padbox = cropbox.to_bottom_left_origin(page_size.height)
            padbox.r = page_size.width - padbox.r
            padbox.t = page_size.height - padbox.t

        image = (
            self._ppage.render(
                scale=scale * 1.5,
                rotation=0,  # no additional rotation
                crop=padbox.as_tuple(),
            )
            .to_pil()
            .resize(size=(round(cropbox.width * scale), round(cropbox.height * scale)))
        )  # We resize the image from 1.5x the given scale to make it sharper.

        return image

    def get_size(self) -> PageSize:
        return PageSize(width=self._ppage.get_width(), height=self._ppage.get_height())

    def unload(self):
        self._ppage = None
        self.text_page = None


class PyPdfiumDocumentBackend(PdfDocumentBackend):
    def __init__(self, path_or_stream: Union[BytesIO, Path]):
        super().__init__(path_or_stream)
        self._pdoc = pdfium.PdfDocument(path_or_stream)

    def page_count(self) -> int:
        return len(self._pdoc)

    def load_page(self, page_no: int) -> PyPdfiumPageBackend:
        return PyPdfiumPageBackend(self._pdoc[page_no])

    def is_valid(self) -> bool:
        return self.page_count() > 0

    def unload(self):
        self._pdoc.close()
        self._pdoc = None
