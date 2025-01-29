import base64
import io
import logging
from typing import List, Optional

import httpx
from docling_core.types.doc import PictureItem
from docling_core.types.doc.document import (  # TODO: move import to docling_core.types.doc
    PictureDescriptionData,
)
from pydantic import BaseModel, ConfigDict

from docling.datamodel.pipeline_options import PicDescApiOptions
from docling.models.pic_description_base_model import PictureDescriptionBaseModel

_log = logging.getLogger(__name__)


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
    model: Optional[str] = None  # returned bu openai
    choices: List[ResponseChoice]
    created: int
    usage: ResponseUsage


class PictureDescriptionApiModel(PictureDescriptionBaseModel):

    def __init__(self, enabled: bool, options: PicDescApiOptions):
        super().__init__(enabled=enabled, options=options)
        self.options: PicDescApiOptions

    def _annotate_image(self, picture: PictureItem) -> PictureDescriptionData:
        assert picture.image is not None

        img_io = io.BytesIO()
        assert picture.image.pil_image is not None
        picture.image.pil_image.save(img_io, "PNG")

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
                        "image_url": {"url": f"data:image/png;base64,{image_base64}"},
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

        return PictureDescriptionData(
            provenance=self.options.provenance,
            text=generated_text,
        )
