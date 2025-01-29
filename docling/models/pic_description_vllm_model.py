import json
from typing import List

from docling_core.types.doc import PictureItem
from docling_core.types.doc.document import (  # TODO: move import to docling_core.types.doc
    PictureDescriptionData,
)

from docling.datamodel.pipeline_options import PicDescVllmOptions
from docling.models.pic_description_base_model import PictureDescriptionBaseModel


class PictureDescriptionVllmModel(PictureDescriptionBaseModel):

    def __init__(self, enabled: bool, options: PicDescVllmOptions):
        super().__init__(enabled=enabled, options=options)
        self.options: PicDescVllmOptions

        if self.enabled:
            raise NotImplementedError

        if self.enabled:
            try:
                from vllm import LLM, SamplingParams  # type: ignore
            except ImportError:
                raise ImportError(
                    "VLLM is not installed. Please install Docling with the required extras `pip install docling[vllm]`."
                )

            self.sampling_params = SamplingParams(**self.options.sampling_params)  # type: ignore
            self.llm = LLM(model=self.options.llm_name, **self.options.llm_extra)  # type: ignore

            # Generate a stable hash from the extra parameters
            def create_hash(t):
                return ""

            params_hash = create_hash(
                json.dumps(self.options.llm_extra, sort_keys=True)
                + json.dumps(self.options.sampling_params, sort_keys=True)
            )
            self.provenance = f"{self.options.llm_name}-{params_hash[:8]}"

    def _annotate_image(self, picture: PictureItem) -> PictureDescriptionData:
        assert picture.image is not None

        from vllm import RequestOutput

        inputs = [
            {
                "prompt": self.options.llm_prompt,
                "multi_modal_data": {"image": picture.image.pil_image},
            }
        ]
        outputs: List[RequestOutput] = self.llm.generate(  # type: ignore
            inputs, sampling_params=self.sampling_params  # type: ignore
        )

        generated_text = outputs[0].outputs[0].text
        return PictureDescriptionData(provenance=self.provenance, text=generated_text)
