import base64
import datetime
import io
import logging
from typing import Any, Dict, Iterable, List, Literal, Optional, Tuple

import httpx
from PIL import Image
from pydantic import AnyUrl, BaseModel, ConfigDict

from docling.datamodel.base_models import Cluster, FigureDescriptionData
from docling.models.img_understand_base_model import (
    ImgUnderstandBaseModel,
    ImgUnderstandOptions,
)

_log = logging.getLogger(__name__)


class ImgUnderstandApiOptions(ImgUnderstandOptions):
    kind: Literal["api"] = "api"

    url: AnyUrl
    headers: Dict[str, str]
    params: Dict[str, Any]
    timeout: float = 20

    llm_prompt: str
    provenance: str


class ChatMessage(BaseModel):
    role: str
    content: str


class ResponseChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str


class ResponseUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ApiResponse(BaseModel):
    model_config = ConfigDict(
        protected_namespaces=(),
    )

    id: str
    model_id: Optional[str] = None  # returned by watsonx
    model: Optional[str] = None  # returned bu openai
    choices: List[ResponseChoice]
    created: int
    usage: ResponseUsage


class ImgUnderstandApiModel(ImgUnderstandBaseModel):

    def __init__(self, enabled: bool, options: ImgUnderstandApiOptions):
        super().__init__(enabled=enabled, options=options)
        self.options: ImgUnderstandApiOptions

    def _annotate_image_batch(
        self, batch: Iterable[Tuple[Cluster, Image.Image]]
    ) -> List[FigureDescriptionData]:

        if not self.enabled:
            return [FigureDescriptionData() for _ in batch]

        results = []
        for cluster, image in batch:
            img_io = io.BytesIO()
            image.save(img_io, "PNG")
            image_base64 = base64.b64encode(img_io.getvalue()).decode("utf-8")

            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": self.options.llm_prompt,
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            },
                        },
                    ],
                }
            ]

            payload = {
                "messages": messages,
                **self.options.params,
            }

            r = httpx.post(
                str(self.options.url),
                headers=self.options.headers,
                json=payload,
                timeout=self.options.timeout,
            )
            if not r.is_success:
                _log.error(f"Error calling the API. Reponse was {r.text}")
            r.raise_for_status()

            api_resp = ApiResponse.model_validate_json(r.text)
            generated_text = api_resp.choices[0].message.content.strip()
            results.append(
                FigureDescriptionData(
                    text=generated_text, provenance=self.options.provenance
                )
            )
            _log.info(f"Generated description: {generated_text}")

        return results
