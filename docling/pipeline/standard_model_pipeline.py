from pathlib import Path

from docling.datamodel.base_models import PipelineOptions
from docling.models.easyocr_model import EasyOcrModel
from docling.models.layout_model import LayoutModel
from docling.models.table_structure_model import TableStructureModel
from docling.pipeline.base_model_pipeline import BaseModelPipeline


class StandardModelPipeline(BaseModelPipeline):
    _layout_model_path = "model_artifacts/layout/beehive_v0.0.5"
    _table_model_path = "model_artifacts/tableformer"

    def __init__(self, artifacts_path: Path, pipeline_options: PipelineOptions):
        super().__init__(artifacts_path, pipeline_options)

        self.model_pipe = [
            EasyOcrModel(
                config={
                    "lang": ["fr", "de", "es", "en"],
                    "enabled": pipeline_options.do_ocr,
                }
            ),
            LayoutModel(
                config={
                    "artifacts_path": artifacts_path
                    / StandardModelPipeline._layout_model_path
                }
            ),
            TableStructureModel(
                config={
                    "artifacts_path": artifacts_path
                    / StandardModelPipeline._table_model_path,
                    "enabled": pipeline_options.do_table_structure,
                    "do_cell_matching": pipeline_options.table_structure_options.do_cell_matching,
                }
            ),
        ]
