import copy
import logging
import random
import time
from typing import Iterable, List

from docling_ibm_models.layoutmodel.layout_predictor import LayoutPredictor
from PIL import ImageDraw

from docling.datamodel.base_models import (
    BoundingBox,
    Cell,
    Cluster,
    CoordOrigin,
    LayoutPrediction,
    Page,
)
from docling.utils import layout_utils as lu

_log = logging.getLogger(__name__)


class LayoutModel:

    TEXT_ELEM_LABELS = [
        "Text",
        "Footnote",
        "Caption",
        "Checkbox-Unselected",
        "Checkbox-Selected",
        "Section-header",
        "Page-header",
        "Page-footer",
        "Code",
        "List-item",
        # "Title"
        # "Formula",
    ]
    PAGE_HEADER_LABELS = ["Page-header", "Page-footer"]

    TABLE_LABEL = "Table"
    FIGURE_LABEL = "Picture"
    FORMULA_LABEL = "Formula"

    def __init__(self, config):
        self.config = config
        self.layout_predictor = LayoutPredictor(
            config["artifacts_path"]
        )  # TODO temporary

    def postprocess(self, clusters: List[Cluster], cells: List[Cell], page_height):
        MIN_INTERSECTION = 0.2
        CLASS_THRESHOLDS = {
            "Caption": 0.35,
            "Footnote": 0.35,
            "Formula": 0.35,
            "List-item": 0.35,
            "Page-footer": 0.35,
            "Page-header": 0.35,
            "Picture": 0.2,  # low threshold adjust to capture chemical structures for examples.
            "Section-header": 0.45,
            "Table": 0.35,
            "Text": 0.45,
            "Title": 0.45,
            "Document Index": 0.45,
            "Code": 0.45,
            "Checkbox-Selected": 0.45,
            "Checkbox-Unselected": 0.45,
            "Form": 0.45,
            "Key-Value Region": 0.45,
        }

        CLASS_REMAPPINGS = {"Document Index": "Table", "Title": "Section-header"}

        _log.debug("================= Start postprocess function ====================")
        start_time = time.time()
        # Apply Confidence Threshold to cluster predictions
        # confidence = self.conf_threshold
        clusters_out = []

        for cluster in clusters:
            confidence = CLASS_THRESHOLDS[cluster.label]
            if cluster.confidence >= confidence:
                # annotation["created_by"] = "high_conf_pred"

                # Remap class labels where needed.
                if cluster.label in CLASS_REMAPPINGS.keys():
                    cluster.label = CLASS_REMAPPINGS[cluster.label]
                clusters_out.append(cluster)

        # map to dictionary clusters and cells, with bottom left origin
        clusters = [
            {
                "id": c.id,
                "bbox": list(
                    c.bbox.to_bottom_left_origin(page_height).as_tuple()
                ),  # TODO
                "confidence": c.confidence,
                "cell_ids": [],
                "type": c.label,
            }
            for c in clusters
        ]

        clusters_out = [
            {
                "id": c.id,
                "bbox": list(
                    c.bbox.to_bottom_left_origin(page_height).as_tuple()
                ),  # TODO
                "confidence": c.confidence,
                "created_by": "high_conf_pred",
                "cell_ids": [],
                "type": c.label,
            }
            for c in clusters_out
        ]

        raw_cells = [
            {
                "id": c.id,
                "bbox": list(
                    c.bbox.to_bottom_left_origin(page_height).as_tuple()
                ),  # TODO
                "text": c.text,
            }
            for c in cells
        ]
        cell_count = len(raw_cells)

        _log.debug("---- 0. Treat cluster overlaps ------")
        clusters_out = lu.remove_cluster_duplicates_by_conf(clusters_out, 0.8)

        _log.debug(
            "---- 1. Initially assign cells to clusters based on minimum intersection ------"
        )
        ## Check for cells included in or touched by clusters:
        clusters_out = lu.assigning_cell_ids_to_clusters(
            clusters_out, raw_cells, MIN_INTERSECTION
        )

        _log.debug("---- 2. Assign Orphans with Low Confidence Detections")
        # Creates a map of cell_id->cluster_id
        (
            clusters_around_cells,
            orphan_cell_indices,
            ambiguous_cell_indices,
        ) = lu.cell_id_state_map(clusters_out, cell_count)

        # Assign orphan cells with lower confidence predictions
        clusters_out, orphan_cell_indices = lu.assign_orphans_with_low_conf_pred(
            clusters_out, clusters, raw_cells, orphan_cell_indices
        )

        # Refresh the cell_ids assignment, after creating new clusters using low conf predictions
        clusters_out = lu.assigning_cell_ids_to_clusters(
            clusters_out, raw_cells, MIN_INTERSECTION
        )

        _log.debug("---- 3. Settle Ambigous Cells")
        # Creates an update map after assignment of cell_id->cluster_id
        (
            clusters_around_cells,
            orphan_cell_indices,
            ambiguous_cell_indices,
        ) = lu.cell_id_state_map(clusters_out, cell_count)

        # Settle pdf cells that belong to multiple clusters
        clusters_out, ambiguous_cell_indices = lu.remove_ambigous_pdf_cell_by_conf(
            clusters_out, raw_cells, ambiguous_cell_indices
        )

        _log.debug("---- 4. Set Orphans as Text")
        (
            clusters_around_cells,
            orphan_cell_indices,
            ambiguous_cell_indices,
        ) = lu.cell_id_state_map(clusters_out, cell_count)

        clusters_out, orphan_cell_indices = lu.set_orphan_as_text(
            clusters_out, clusters, raw_cells, orphan_cell_indices
        )

        _log.debug("---- 5. Merge Cells & and adapt the bounding boxes")
        # Merge cells orphan cells
        clusters_out = lu.merge_cells(clusters_out)

        # Clean up clusters that remain from merged and unreasonable clusters
        clusters_out = lu.clean_up_clusters(
            clusters_out,
            raw_cells,
            merge_cells=True,
            img_table=True,
            one_cell_table=True,
        )

        new_clusters = lu.adapt_bboxes(raw_cells, clusters_out, orphan_cell_indices)
        clusters_out = new_clusters

        ## We first rebuild where every cell is now:
        ##   Now we write into a prediction cells list, not into the raw cells list.
        ##   As we don't need previous labels, we best overwrite any old list, because that might
        ##   have been sorted differently.
        (
            clusters_around_cells,
            orphan_cell_indices,
            ambiguous_cell_indices,
        ) = lu.cell_id_state_map(clusters_out, cell_count)

        target_cells = []
        for ix, cell in enumerate(raw_cells):
            new_cell = {
                "id": ix,
                "rawcell_id": ix,
                "label": "None",
                "bbox": cell["bbox"],
                "text": cell["text"],
            }
            for cluster_index in clusters_around_cells[
                ix
            ]:  # By previous analysis, this is always 1 cluster.
                new_cell["label"] = clusters_out[cluster_index]["type"]
            target_cells.append(new_cell)
            # _log.debug("New label of cell " + str(ix) + " is " + str(new_cell["label"]))
        cells_out = target_cells

        ## -------------------------------
        ## Sort clusters into reasonable reading order, and sort the cells inside each cluster
        _log.debug("---- 5. Sort clusters in reading order ------")
        sorted_clusters = lu.produce_reading_order(
            clusters_out, "raw_cell_ids", "raw_cell_ids", True
        )
        clusters_out = sorted_clusters

        # end_time = timer()
        _log.debug("---- End of postprocessing function ------")
        end_time = time.time() - start_time
        _log.debug(f"Finished post processing in seconds={end_time:.3f}")

        cells_out = [
            Cell(
                id=c["id"],
                bbox=BoundingBox.from_tuple(
                    coord=c["bbox"], origin=CoordOrigin.BOTTOMLEFT
                ).to_top_left_origin(page_height),
                text=c["text"],
            )
            for c in cells_out
        ]
        clusters_out_new = []
        for c in clusters_out:
            cluster_cells = [ccell for ccell in cells_out if ccell.id in c["cell_ids"]]
            c_new = Cluster(
                id=c["id"],
                bbox=BoundingBox.from_tuple(
                    coord=c["bbox"], origin=CoordOrigin.BOTTOMLEFT
                ).to_top_left_origin(page_height),
                confidence=c["confidence"],
                label=c["type"],
                cells=cluster_cells,
            )
            clusters_out_new.append(c_new)

        return clusters_out_new, cells_out

    def __call__(self, page_batch: Iterable[Page]) -> Iterable[Page]:
        for page in page_batch:
            clusters = []
            for ix, pred_item in enumerate(
                self.layout_predictor.predict(page.get_image(scale=1.0))
            ):
                cluster = Cluster(
                    id=ix,
                    label=pred_item["label"],
                    confidence=pred_item["confidence"],
                    bbox=BoundingBox.model_validate(pred_item),
                    cells=[],
                )

                clusters.append(cluster)

            # Map cells to clusters
            # TODO: Remove, postprocess should take care of it anyway.
            for cell in page.cells:
                for cluster in clusters:
                    if not cell.bbox.area() > 0:
                        overlap_frac = 0.0
                    else:
                        overlap_frac = (
                            cell.bbox.intersection_area_with(cluster.bbox)
                            / cell.bbox.area()
                        )

                    if overlap_frac > 0.5:
                        cluster.cells.append(cell)

            # Pre-sort clusters
            # clusters = self.sort_clusters_by_cell_order(clusters)

            # DEBUG code:
            def draw_clusters_and_cells():
                image = copy.deepcopy(page.image)
                draw = ImageDraw.Draw(image)
                for c in clusters:
                    x0, y0, x1, y1 = c.bbox.as_tuple()
                    draw.rectangle([(x0, y0), (x1, y1)], outline="green")

                    cell_color = (
                        random.randint(30, 140),
                        random.randint(30, 140),
                        random.randint(30, 140),
                    )
                    for tc in c.cells:  # [:1]:
                        x0, y0, x1, y1 = tc.bbox.as_tuple()
                        draw.rectangle([(x0, y0), (x1, y1)], outline=cell_color)
                image.show()

            # draw_clusters_and_cells()

            clusters, page.cells = self.postprocess(
                clusters, page.cells, page.size.height
            )

            # draw_clusters_and_cells()

            page.predictions.layout = LayoutPrediction(clusters=clusters)

            yield page
