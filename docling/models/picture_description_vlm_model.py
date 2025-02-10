from pathlib import Path
from typing import Iterable, Optional, Union

from PIL import Image

from docling.datamodel.pipeline_options import (
    AcceleratorOptions,
    PictureDescriptionVlmOptions,
)
from docling.models.picture_description_base_model import PictureDescriptionBaseModel
from docling.utils.accelerator_utils import decide_device


class PictureDescriptionVlmModel(PictureDescriptionBaseModel):

    def __init__(
        self,
        enabled: bool,
        artifacts_path: Optional[Union[Path, str]],
        options: PictureDescriptionVlmOptions,
        accelerator_options: AcceleratorOptions,
    ):
        super().__init__(enabled=enabled, options=options)
        self.options: PictureDescriptionVlmOptions

        if self.enabled:

            if artifacts_path is None:
                artifacts_path = self.download_models(repo_id=self.options.repo_id)
            else:
                artifacts_path = Path(artifacts_path) / self.options.repo_cache_folder

            self.device = decide_device(accelerator_options.device)

            try:
                import torch
                from transformers import AutoModelForVision2Seq, AutoProcessor
            except ImportError:
                raise ImportError(
                    "transformers >=4.46 is not installed. Please install Docling with the required extras `pip install docling[vlm]`."
                )

            # Initialize processor and model
            self.processor = AutoProcessor.from_pretrained(self.options.repo_id)
            self.model = AutoModelForVision2Seq.from_pretrained(
                self.options.repo_id,
                torch_dtype=torch.bfloat16,
                _attn_implementation=(
                    "flash_attention_2" if self.device.startswith("cuda") else "eager"
                ),
            ).to(self.device)

            self.provenance = f"{self.options.repo_id}"

    @staticmethod
    def download_models(
        repo_id: str,
        local_dir: Optional[Path] = None,
        force: bool = False,
        progress: bool = False,
    ) -> Path:
        from huggingface_hub import snapshot_download
        from huggingface_hub.utils import disable_progress_bars

        if not progress:
            disable_progress_bars()
        download_path = snapshot_download(
            repo_id=repo_id,
            force_download=force,
            local_dir=local_dir,
        )

        return Path(download_path)

    def _annotate_images(self, images: Iterable[Image.Image]) -> Iterable[str]:
        from transformers import GenerationConfig

        # Create input messages
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image"},
                    {"type": "text", "text": self.options.prompt},
                ],
            },
        ]

        # TODO: do batch generation

        for image in images:
            # Prepare inputs
            prompt = self.processor.apply_chat_template(
                messages, add_generation_prompt=True
            )
            inputs = self.processor(text=prompt, images=[image], return_tensors="pt")
            inputs = inputs.to(self.device)

            # Generate outputs
            generated_ids = self.model.generate(
                **inputs,
                generation_config=GenerationConfig(**self.options.generation_config),
            )
            generated_texts = self.processor.batch_decode(
                generated_ids[:, inputs["input_ids"].shape[1] :],
                skip_special_tokens=True,
            )

            yield generated_texts[0].strip()
