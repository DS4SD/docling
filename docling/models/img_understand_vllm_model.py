import json
import logging
from typing import Any, Dict, Iterable, List, Literal, Tuple

from PIL import Image

from docling.datamodel.base_models import Cluster, FigureDescriptionData
from docling.models.img_understand_base_model import (
    ImgUnderstandBaseModel,
    ImgUnderstandOptions,
)
from docling.utils.utils import create_hash

_log = logging.getLogger(__name__)


class ImgUnderstandVllmOptions(ImgUnderstandOptions):
    kind: Literal["vllm"] = "vllm"

    # For more example parameters see https://docs.vllm.ai/en/latest/getting_started/examples/offline_inference_vision_language.html

    # Parameters for LLaVA-1.6/LLaVA-NeXT
    llm_name: str = "llava-hf/llava-v1.6-mistral-7b-hf"
    llm_prompt: str = "[INST] <image>\nDescribe the image in details. [/INST]"
    llm_extra: Dict[str, Any] = dict(max_model_len=8192)

    # Parameters for Phi-3-Vision
    # llm_name: str = "microsoft/Phi-3-vision-128k-instruct"
    # llm_prompt: str = "<|user|>\n<|image_1|>\nDescribe the image in details.<|end|>\n<|assistant|>\n"
    # llm_extra: Dict[str, Any] = dict(max_num_seqs=5, trust_remote_code=True)

    sampling_params: Dict[str, Any] = dict(max_tokens=64, seed=42)


class ImgUnderstandVllmModel(ImgUnderstandBaseModel):

    def __init__(self, enabled: bool, options: ImgUnderstandVllmOptions):
        super().__init__(enabled=enabled, options=options)
        self.options: ImgUnderstandVllmOptions

        if self.enabled:
            try:
                from vllm import LLM, SamplingParams
            except ImportError:
                raise ImportError(
                    "VLLM is not installed. Please install Docling with the required extras `pip install docling[vllm]`."
                )

            self.sampling_params = SamplingParams(**self.options.sampling_params)
            self.llm = LLM(model=self.options.llm_name, **self.options.llm_extra)

            # Generate a stable hash from the extra parameters
            params_hash = create_hash(
                json.dumps(self.options.llm_extra, sort_keys=True)
                + json.dumps(self.options.sampling_params, sort_keys=True)
            )
            self.provenance = f"{self.options.llm_name}-{params_hash[:8]}"

    def _annotate_image_batch(
        self, batch: Iterable[Tuple[Cluster, Image.Image]]
    ) -> List[FigureDescriptionData]:

        if not self.enabled:
            return [FigureDescriptionData() for _ in batch]

        from vllm import RequestOutput

        inputs = [
            {
                "prompt": self.options.llm_prompt,
                "multi_modal_data": {"image": im},
            }
            for _, im in batch
        ]
        outputs: List[RequestOutput] = self.llm.generate(
            inputs, sampling_params=self.sampling_params
        )

        results = []
        for o in outputs:
            generated_text = o.outputs[0].text
            results.append(
                FigureDescriptionData(text=generated_text, provenance=self.provenance)
            )
            _log.info(f"Generated description: {generated_text}")

        return results
