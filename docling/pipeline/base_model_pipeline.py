from pathlib import Path
from typing import Callable, Iterable, List

from docling.datamodel.base_models import Page
from docling.datamodel.pipeline_options import PipelineOptions


class BaseModelPipeline:
    def __init__(self, artifacts_path: Path, pipeline_options: PipelineOptions):
        self.model_pipe: List[Callable] = []
        self.artifacts_path = artifacts_path
        self.pipeline_options = pipeline_options

    def apply(self, page_batch: Iterable[Page]) -> Iterable[Page]:
        for model in self.model_pipe:
            page_batch = model(page_batch)

        yield from page_batch
