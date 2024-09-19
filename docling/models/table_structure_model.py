import copy
from pathlib import Path
from typing import Iterable, List

import numpy
from docling_ibm_models.tableformer.data_management.tf_predictor import TFPredictor
from PIL import ImageDraw

from docling.datamodel.base_models import (
    BoundingBox,
    Page,
    TableCell,
    TableElement,
    TableStructurePrediction,
)
from docling.datamodel.pipeline_options import TableFormerMode


class TableStructureModel:
    def __init__(self, config):
        self.config = config
        self.do_cell_matching = config["do_cell_matching"]
        self.mode = config["mode"]

        self.enabled = config["enabled"]
        if self.enabled:
            artifacts_path: Path = config["artifacts_path"]

            if self.mode == TableFormerMode.ACCURATE:
                artifacts_path = artifacts_path / "fat"

            # Third Party
            import docling_ibm_models.tableformer.common as c

            self.tm_config = c.read_config(f"{artifacts_path}/tm_config.json")
            self.tm_config["model"]["save_dir"] = artifacts_path
            self.tm_model_type = self.tm_config["model"]["type"]

            self.tf_predictor = TFPredictor(self.tm_config)
            self.scale = 2.0  # Scale up table input images to 144 dpi

    def draw_table_and_cells(self, page: Page, tbl_list: List[TableElement]):
        image = (
            page._backend.get_page_image()
        )  # make new image to avoid drawing on the saved ones
        draw = ImageDraw.Draw(image)

        for table_element in tbl_list:
            x0, y0, x1, y1 = table_element.cluster.bbox.as_tuple()
            draw.rectangle([(x0, y0), (x1, y1)], outline="red")

            for tc in table_element.table_cells:
                x0, y0, x1, y1 = tc.bbox.as_tuple()
                if tc.column_header:
                    width = 3
                else:
                    width = 1
                draw.rectangle([(x0, y0), (x1, y1)], outline="blue", width=width)
                draw.text(
                    (x0 + 3, y0 + 3),
                    text=f"{tc.start_row_offset_idx}, {tc.start_col_offset_idx}",
                    fill="black",
                )

        image.show()

    def __call__(self, page_batch: Iterable[Page]) -> Iterable[Page]:

        if not self.enabled:
            yield from page_batch
            return

        for page in page_batch:

            page.predictions.tablestructure = TableStructurePrediction()  # dummy

            in_tables = [
                (
                    cluster,
                    [
                        round(cluster.bbox.l) * self.scale,
                        round(cluster.bbox.t) * self.scale,
                        round(cluster.bbox.r) * self.scale,
                        round(cluster.bbox.b) * self.scale,
                    ],
                )
                for cluster in page.predictions.layout.clusters
                if cluster.label == "Table"
            ]
            if not len(in_tables):
                yield page
                continue

            tokens = []
            for c in page.cells:
                for cluster, _ in in_tables:
                    if c.bbox.area() > 0:
                        if (
                            c.bbox.intersection_area_with(cluster.bbox) / c.bbox.area()
                            > 0.2
                        ):
                            # Only allow non empty stings (spaces) into the cells of a table
                            if len(c.text.strip()) > 0:
                                new_cell = copy.deepcopy(c)
                                new_cell.bbox = new_cell.bbox.scaled(scale=self.scale)

                                tokens.append(new_cell.model_dump())

            page_input = {
                "tokens": tokens,
                "width": page.size.width * self.scale,
                "height": page.size.height * self.scale,
            }
            page_input["image"] = numpy.asarray(page.get_image(scale=self.scale))

            table_clusters, table_bboxes = zip(*in_tables)

            if len(table_bboxes):
                tf_output = self.tf_predictor.multi_table_predict(
                    page_input, table_bboxes, do_matching=self.do_cell_matching
                )

                for table_cluster, table_out in zip(table_clusters, tf_output):
                    table_cells = []
                    for element in table_out["tf_responses"]:

                        if not self.do_cell_matching:
                            the_bbox = BoundingBox.model_validate(
                                element["bbox"]
                            ).scaled(1 / self.scale)
                            text_piece = page._backend.get_text_in_rect(the_bbox)
                            element["bbox"]["token"] = text_piece

                        tc = TableCell.model_validate(element)
                        if self.do_cell_matching:
                            tc.bbox = tc.bbox.scaled(1 / self.scale)
                        table_cells.append(tc)

                    # Retrieving cols/rows, after post processing:
                    num_rows = table_out["predict_details"]["num_rows"]
                    num_cols = table_out["predict_details"]["num_cols"]
                    otsl_seq = table_out["predict_details"]["prediction"]["rs_seq"]

                    tbl = TableElement(
                        otsl_seq=otsl_seq,
                        table_cells=table_cells,
                        num_rows=num_rows,
                        num_cols=num_cols,
                        id=table_cluster.id,
                        page_no=page.page_no,
                        cluster=table_cluster,
                        label="Table",
                    )

                    page.predictions.tablestructure.table_map[table_cluster.id] = tbl

                # For debugging purposes:
                # self.draw_table_and_cells(page, page.predictions.tablestructure.table_map.values())

            yield page
