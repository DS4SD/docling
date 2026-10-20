# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

from PIL import Image


def to_rgb(image: Image.Image) -> Image.Image:
    """Convert an image to RGB, flattening any transparency onto white.

    A plain ``convert("RGB")`` drops the alpha channel and keeps the colour
    stored under it, which is usually black for fully transparent pixels. Dark
    content on a transparent background would then become a black image.
    Palette images with ``tRNS`` transparency also go through RGBA, which
    avoids the Pillow warning for transparency expressed in bytes.
    """
    if image.mode in ("RGBA", "LA", "PA") or "transparency" in image.info:
        rgba = image.convert("RGBA")
        background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        return Image.alpha_composite(background, rgba).convert("RGB")
    return image.convert("RGB")
