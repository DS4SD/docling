from typing import Iterable

import numpy
from docling_ibm_models.tableformer.data_management.tf_predictor import TFPredictor

from docling.datamodel.base_models import (
    BoundingBox,
    Page,
    TableCell,
    TableElement,
    TableStructurePrediction,
)


class TableStructureModel:
    def __init__(self, config):
        self.config = config
        self.do_cell_matching = config["do_cell_matching"]

        self.enabled = config["enabled"]
        if self.enabled:
            artifacts_path = config["artifacts_path"]
            # Third Party
            import docling_ibm_models.tableformer.common as c

            self.tm_config = c.read_config(f"{artifacts_path}/tm_config.json")
            self.tm_config["model"]["save_dir"] = artifacts_path
            self.tm_model_type = self.tm_config["model"]["type"]

            self.tf_predictor = TFPredictor(self.tm_config)

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
                        round(cluster.bbox.l),
                        round(cluster.bbox.t),
                        round(cluster.bbox.r),
                        round(cluster.bbox.b),
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
                                tokens.append(c.model_dump())

            iocr_page = {
                "image": numpy.asarray(page.image),
                "tokens": tokens,
                "width": page.size.width,
                "height": page.size.height,
            }

            table_clusters, table_bboxes = zip(*in_tables)

            if len(table_bboxes):
                tf_output = self.tf_predictor.multi_table_predict(
                    iocr_page, table_bboxes, do_matching=self.do_cell_matching
                )

                for table_cluster, table_out in zip(table_clusters, tf_output):
                    table_cells = []
                    for element in table_out["tf_responses"]:

                        if not self.do_cell_matching:
                            the_bbox = BoundingBox.model_validate(element["bbox"])
                            text_piece = page._backend.get_text_in_rect(the_bbox)
                            element["bbox"]["token"] = text_piece

                        tc = TableCell.model_validate(element)
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

            yield page
