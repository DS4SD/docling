from pathlib import Path
from typing import Union

from pydantic import BaseModel, Field

from docling.datamodel.base_models import PipelineOptions
from docling.models.img_understand_api_model import (
    ImgUnderstandApiModel,
    ImgUnderstandApiOptions,
)
from docling.models.img_understand_vllm_model import (
    ImgUnderstandVllmModel,
    ImgUnderstandVllmOptions,
)
from docling.pipeline.standard_model_pipeline import StandardModelPipeline


class ImgUnderstandPipelineOptions(PipelineOptions):
    do_img_understand: bool = True
    img_understand_options: Union[ImgUnderstandApiOptions, ImgUnderstandVllmOptions] = (
        Field(ImgUnderstandVllmOptions(), discriminator="kind")
    )


class ImgUnderstandPipeline(StandardModelPipeline):

    def __init__(
        self, artifacts_path: Path, pipeline_options: ImgUnderstandPipelineOptions
    ):
        super().__init__(artifacts_path, pipeline_options)

        if isinstance(
            pipeline_options.img_understand_options, ImgUnderstandVllmOptions
        ):
            self.model_pipe.append(
                ImgUnderstandVllmModel(
                    enabled=pipeline_options.do_img_understand,
                    options=pipeline_options.img_understand_options,
                )
            )
        elif isinstance(
            pipeline_options.img_understand_options, ImgUnderstandApiOptions
        ):
            self.model_pipe.append(
                ImgUnderstandApiModel(
                    enabled=pipeline_options.do_img_understand,
                    options=pipeline_options.img_understand_options,
                )
            )
        else:
            raise RuntimeError(
                f"The specified imgage understanding kind is not supported: {pipeline_options.img_understand_options.kind}."
            )
