import copy
import logging
import random
import time
from pathlib import Path
from typing import Iterable, List

from docling_core.types.doc import CoordOrigin, DocItemLabel
from docling_ibm_models.layoutmodel.layout_predictor import LayoutPredictor
from PIL import Image, ImageDraw, ImageFont

from docling.datamodel.base_models import (
    BoundingBox,
    Cell,
    Cluster,
    DocTagsPrediction,
    LayoutPrediction,
    Page,
)
from docling.datamodel.document import ConversionResult
from docling.datamodel.pipeline_options import AcceleratorDevice, AcceleratorOptions
from docling.datamodel.settings import settings
from docling.models.base_model import BasePageModel
from docling.utils.accelerator_utils import decide_device
from docling.utils.layout_postprocessor import LayoutPostprocessor
from docling.utils.profiling import TimeRecorder

_log = logging.getLogger(__name__)


class SmolDoclingModel(BasePageModel):

    def __init__(self, artifacts_path: Path, accelerator_options: AcceleratorOptions):
        device = decide_device(accelerator_options.device)

        # self.your_vlm_predictor(..., device) = None # TODO

    def __call__(
        self, conv_res: ConversionResult, page_batch: Iterable[Page]
    ) -> Iterable[Page]:

        for page in page_batch:
            assert page._backend is not None
            if not page._backend.is_valid():
                yield page
            else:
                with TimeRecorder(conv_res, "smolvlm"):
                    assert page.size is not None

                    hi_res_image = page.get_image(scale=2.0)  # 144dpi

                    # Call your self.your_vlm_predictor with the page image as input (hi_res_image)
                    # populate page_tags
                    page_tags = ""

                    page.predictions.doctags = DocTagsPrediction(tag_string=page_tags)

                yield page
