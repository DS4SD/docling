import logging
import time
from pathlib import Path
from typing import Iterable, List, Optional

import torch
from docling_core.types.doc.document import DEFAULT_EXPORT_LABELS
from transformers import (  # type: ignore
    AutoProcessor,
    BitsAndBytesConfig,
    Idefics3ForConditionalGeneration,
)

from docling.datamodel.base_models import DocTagsPrediction, Page
from docling.datamodel.document import ConversionResult
from docling.datamodel.pipeline_options import AcceleratorDevice, AcceleratorOptions
from docling.datamodel.settings import settings
from docling.models.base_model import BasePageModel
from docling.utils.accelerator_utils import decide_device
from docling.utils.profiling import TimeRecorder

_log = logging.getLogger(__name__)


class SmolDoclingModel(BasePageModel):

    def __init__(self, artifacts_path: Path, accelerator_options: AcceleratorOptions):
        device = decide_device(accelerator_options.device)
        self.device = device
        _log.info("Available device for SmolDocling: {}".format(device))

        # PARAMETERS:
        self.param_question = "Perform Layout Analysis."
        self.param_quantization_config = BitsAndBytesConfig(
            load_in_8bit=True, llm_int8_threshold=6.0
        )
        self.param_quantized = False

        self.processor = AutoProcessor.from_pretrained(artifacts_path)
        if not self.param_quantized:
            self.vlm_model = Idefics3ForConditionalGeneration.from_pretrained(
                artifacts_path,
                device_map=device,
                torch_dtype=torch.bfloat16,
                # _attn_implementation="flash_attention_2",
            )
            self.vlm_model = self.vlm_model.to(device)
        else:
            self.vlm_model = Idefics3ForConditionalGeneration.from_pretrained(
                artifacts_path,
                device_map=device,
                torch_dtype="auto",
                quantization_config=self.param_quantization_config,
            )

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
                    # populate page_tags with predicted doc tags
                    page_tags = ""

                    if hi_res_image:
                        if hi_res_image.mode != "RGB":
                            hi_res_image = hi_res_image.convert("RGB")

                    messages = [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "This is a page from a document.",
                                },
                                {"type": "image"},
                                {"type": "text", "text": self.param_question},
                            ],
                        }
                    ]
                    prompt = self.processor.apply_chat_template(
                        messages, add_generation_prompt=False
                    )
                    inputs = self.processor(
                        text=prompt, images=[hi_res_image], return_tensors="pt"
                    )
                    inputs = {k: v.to(self.device) for k, v in inputs.items()}
                    prompt = prompt.replace("<end_of_utterance>", "")

                    start_time = time.time()
                    # Call model to generate:
                    generated_ids = self.vlm_model.generate(
                        **inputs, max_new_tokens=4096
                    )

                    generation_time = time.time() - start_time

                    generated_texts = self.processor.batch_decode(
                        generated_ids, skip_special_tokens=True
                    )[0]
                    num_tokens = len(generated_ids[0])
                    generated_texts = generated_texts.replace("Assistant: ", "")
                    page_tags = generated_texts

                    inference_time = time.time() - start_time
                    tokens_per_second = num_tokens / generation_time
                    print("")
                    print(f"Page Inference Time: {inference_time:.2f} seconds")
                    print(f"Tokens/sec: {tokens_per_second:.2f}")
                    print("")
                    print("Page predictions:")
                    print(page_tags)

                    page.predictions.doctags = DocTagsPrediction(tag_string=page_tags)

                yield page
