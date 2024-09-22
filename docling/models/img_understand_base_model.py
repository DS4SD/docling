import logging
import time
from typing import Iterable, List, Literal, Tuple

from PIL import Image
from pydantic import BaseModel

from docling.datamodel.base_models import (
    Cluster,
    FigureData,
    FigureDescriptionData,
    FigureElement,
    FigurePrediction,
    Page,
)

_log = logging.getLogger(__name__)


class ImgUnderstandOptions(BaseModel):
    kind: str
    batch_size: int = 8
    scale: float = 2

    # if the relative area of the image with respect to the whole image page
    # is larger than this threshold it will be processed, otherwise not.
    # TODO: implement the skip logic
    min_area: float = 0.05


class ImgUnderstandBaseModel:

    def __init__(self, enabled: bool, options: ImgUnderstandOptions):
        self.enabled = enabled
        self.options = options

    def _annotate_image_batch(
        self, batch: Iterable[Tuple[Cluster, Image.Image]]
    ) -> List[FigureDescriptionData]:
        raise NotImplemented()

    def _flush_merge(
        self,
        page: Page,
        cluster_figure_batch: List[Tuple[Cluster, Image.Image]],
        figures_prediction: FigurePrediction,
    ):
        start_time = time.time()
        results_batch = self._annotate_image_batch(cluster_figure_batch)
        assert len(results_batch) == len(
            cluster_figure_batch
        ), "The returned annotations is not matching the input size"
        end_time = time.time()
        _log.info(
            f"Batch of {len(results_batch)} images processed in {end_time-start_time:.1f} seconds. Time per image is {(end_time-start_time) / len(results_batch):.3f} seconds."
        )

        for (cluster, _), desc_data in zip(cluster_figure_batch, results_batch):
            if not cluster.id in figures_prediction.figure_map:
                figures_prediction.figure_map[cluster.id] = FigureElement(
                    label=cluster.label,
                    id=cluster.id,
                    data=FigureData(desciption=desc_data),
                    cluster=cluster,
                    page_no=page.page_no,
                )
            elif figures_prediction.figure_map[cluster.id].data.description is None:
                figures_prediction.figure_map[cluster.id].data.description = desc_data
            else:
                _log.warning(
                    f"Conflicting predictions. "
                    f"Another model ({figures_prediction.figure_map[cluster.id].data.description.provenance}) "
                    f"was already predicting an image description. The new prediction will be skipped."
                )

    def __call__(self, page_batch: Iterable[Page]) -> Iterable[Page]:

        if not self.enabled:
            yield from page_batch
            return

        for page in page_batch:

            # This model could be the first one initializing figures_prediction
            if page.predictions.figures_prediction is None:
                page.predictions.figures_prediction = FigurePrediction()

            # Select the picture clusters
            in_clusters = []
            for cluster in page.predictions.layout.clusters:
                if cluster.label != "Picture":
                    continue

                crop_bbox = cluster.bbox.scaled(
                    scale=self.options.scale
                ).to_top_left_origin(page_height=page.size.height * self.options.scale)
                in_clusters.append(
                    (
                        cluster,
                        crop_bbox.as_tuple(),
                    )
                )

            if not len(in_clusters):
                yield page
                continue

            # save classifications using proper object
            if (
                page.predictions.figures_prediction.figure_count > 0
                and page.predictions.figures_prediction.figure_count != len(in_clusters)
            ):
                raise RuntimeError(
                    "Different models predicted a different number of figures."
                )
            page.predictions.figures_prediction.figure_count = len(in_clusters)

            cluster_figure_batch = []
            page_image = page.get_image(scale=self.options.scale)
            if page_image is None:
                raise RuntimeError("The page image cannot be generated.")

            for cluster, figure_bbox in in_clusters:
                figure = page_image.crop(figure_bbox)
                cluster_figure_batch.append((cluster, figure))

                # if enough figures then flush
                if len(cluster_figure_batch) == self.options.batch_size:
                    self._flush_merge(
                        page=page,
                        cluster_figure_batch=cluster_figure_batch,
                        figures_prediction=page.predictions.figures_prediction,
                    )
                    cluster_figure_batch = []

            # final flush
            if len(cluster_figure_batch) > 0:
                self._flush_merge(
                    page=page,
                    cluster_figure_batch=cluster_figure_batch,
                    figures_prediction=page.predictions.figures_prediction,
                )
                cluster_figure_batch = []

            yield page
