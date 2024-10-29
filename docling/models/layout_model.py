import copy
import logging
import random
import time
from pathlib import Path
from typing import Iterable, List

from docling_core.types.doc import CoordOrigin, DocItemLabel
from docling_ibm_models.layoutmodel.layout_predictor import LayoutPredictor
from PIL import ImageDraw

from docling.datamodel.base_models import (
    BoundingBox,
    Cell,
    Cluster,
    LayoutPrediction,
    Page,
)
from docling.datamodel.document import ConversionResult
from docling.datamodel.settings import settings
from docling.models.base_model import BasePageModel
from docling.utils import layout_utils as lu
from docling.utils.profiling import TimeRecorder

_log = logging.getLogger(__name__)


class LayoutModel(BasePageModel):

    TEXT_ELEM_LABELS = [
        DocItemLabel.TEXT,
        DocItemLabel.FOOTNOTE,
        DocItemLabel.CAPTION,
        DocItemLabel.CHECKBOX_UNSELECTED,
        DocItemLabel.CHECKBOX_SELECTED,
        DocItemLabel.SECTION_HEADER,
        DocItemLabel.PAGE_HEADER,
        DocItemLabel.PAGE_FOOTER,
        DocItemLabel.CODE,
        DocItemLabel.LIST_ITEM,
        # "Formula",
    ]
    PAGE_HEADER_LABELS = [DocItemLabel.PAGE_HEADER, DocItemLabel.PAGE_FOOTER]

    TABLE_LABEL = DocItemLabel.TABLE
    FIGURE_LABEL = DocItemLabel.PICTURE
    FORMULA_LABEL = DocItemLabel.FORMULA

    def __init__(self, artifacts_path: Path):
        self.layout_predictor = LayoutPredictor(artifacts_path)  # TODO temporary

    def postprocess(self, clusters_in: List[Cluster], cells: List[Cell], page_height):
        MIN_INTERSECTION = 0.2
        CLASS_THRESHOLDS = {
            DocItemLabel.CAPTION: 0.35,
            DocItemLabel.FOOTNOTE: 0.35,
            DocItemLabel.FORMULA: 0.35,
            DocItemLabel.LIST_ITEM: 0.35,
            DocItemLabel.PAGE_FOOTER: 0.35,
            DocItemLabel.PAGE_HEADER: 0.35,
            DocItemLabel.PICTURE: 0.2,  # low threshold adjust to capture chemical structures for examples.
            DocItemLabel.SECTION_HEADER: 0.45,
            DocItemLabel.TABLE: 0.35,
            DocItemLabel.TEXT: 0.45,
            DocItemLabel.TITLE: 0.45,
            DocItemLabel.DOCUMENT_INDEX: 0.45,
            DocItemLabel.CODE: 0.45,
            DocItemLabel.CHECKBOX_SELECTED: 0.45,
            DocItemLabel.CHECKBOX_UNSELECTED: 0.45,
            DocItemLabel.FORM: 0.45,
            DocItemLabel.KEY_VALUE_REGION: 0.45,
        }

        CLASS_REMAPPINGS = {
            DocItemLabel.DOCUMENT_INDEX: DocItemLabel.TABLE,
            DocItemLabel.TITLE: DocItemLabel.SECTION_HEADER,
        }

        _log.debug("================= Start postprocess function ====================")
        start_time = time.time()
        # Apply Confidence Threshold to cluster predictions
        # confidence = self.conf_threshold
        clusters_mod = []

        for cluster in clusters_in:
            confidence = CLASS_THRESHOLDS[cluster.label]
            if cluster.confidence >= confidence:
                # annotation["created_by"] = "high_conf_pred"

                # Remap class labels where needed.
                if cluster.label in CLASS_REMAPPINGS.keys():
                    cluster.label = CLASS_REMAPPINGS[cluster.label]
                clusters_mod.append(cluster)

        # map to dictionary clusters and cells, with bottom left origin
        clusters_orig = [
            {
                "id": c.id,
                "bbox": list(
                    c.bbox.to_bottom_left_origin(page_height).as_tuple()
                ),  # TODO
                "confidence": c.confidence,
                "cell_ids": [],
                "type": c.label,
            }
            for c in clusters_in
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
            for c in clusters_mod
        ]

        del clusters_mod

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
            clusters_out, clusters_orig, raw_cells, orphan_cell_indices
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
            clusters_out, clusters_orig, raw_cells, orphan_cell_indices
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

        cells_out_new = [
            Cell(
                id=c["id"],  # type: ignore
                bbox=BoundingBox.from_tuple(
                    coord=c["bbox"], origin=CoordOrigin.BOTTOMLEFT  # type: ignore
                ).to_top_left_origin(page_height),
                text=c["text"],  # type: ignore
            )
            for c in cells_out
        ]

        del cells_out

        clusters_out_new = []
        for c in clusters_out:
            cluster_cells = [
                ccell for ccell in cells_out_new if ccell.id in c["cell_ids"]  # type: ignore
            ]
            c_new = Cluster(
                id=c["id"],  # type: ignore
                bbox=BoundingBox.from_tuple(
                    coord=c["bbox"], origin=CoordOrigin.BOTTOMLEFT  # type: ignore
                ).to_top_left_origin(page_height),
                confidence=c["confidence"],  # type: ignore
                label=DocItemLabel(c["type"]),
                cells=cluster_cells,
            )
            clusters_out_new.append(c_new)

        return clusters_out_new, cells_out_new

    def __call__(
        self, conv_res: ConversionResult, page_batch: Iterable[Page]
    ) -> Iterable[Page]:

        for page in page_batch:
            assert page._backend is not None
            if not page._backend.is_valid():
                yield page
            else:
                with TimeRecorder(conv_res, "layout"):
                    assert page.size is not None

                    clusters = []
                    for ix, pred_item in enumerate(
                        self.layout_predictor.predict(page.get_image(scale=1.0))
                    ):
                        label = DocItemLabel(
                            pred_item["label"]
                            .lower()
                            .replace(" ", "_")
                            .replace("-", "_")
                        )  # Temporary, until docling-ibm-model uses docling-core types
                        cluster = Cluster(
                            id=ix,
                            label=label,
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
                    def draw_clusters_and_cells(show: bool = False):
                        image = copy.deepcopy(page.image)
                        if image is not None:
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
                                    draw.rectangle(
                                        [(x0, y0), (x1, y1)], outline=cell_color
                                    )
                            if show:
                                image.show()
                            else:
                                out_path: Path = (
                                    Path(settings.debug.debug_output_path)
                                    / f"debug_{conv_res.input.file.stem}"
                                )
                                out_path.mkdir(parents=True, exist_ok=True)

                                out_file = (
                                    out_path / f"layout_page_{page.page_no:05}.png"
                                )
                                image.save(str(out_file), format="png")

                    # draw_clusters_and_cells()

                    clusters, page.cells = self.postprocess(
                        clusters, page.cells, page.size.height
                    )

                    page.predictions.layout = LayoutPrediction(clusters=clusters)

                if settings.debug.visualize_layout:
                    draw_clusters_and_cells()

                yield page
