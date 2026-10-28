"""OpenAI image-edit wrapper. Model name from env (OPENAI_IMAGE_MODEL),
never hard-coded.

Returns the raw PNG bytes; the caller crops/resizes to the target 1280x720.
Tests inject a fake client via _client= so no live calls happen in CI.
"""
from __future__ import annotations

import base64
import io
import os
from dataclasses import dataclass
from typing import Any

from PIL import Image


@dataclass
class ImageEditResult:
    png_bytes: bytes
    requested_size: str
    model: str


class OpenAIImageEditor:
    def __init__(self, *, model: str | None = None, api_key: str | None = None,
                 _client: Any = None) -> None:
        self.model = model or os.environ.get("OPENAI_IMAGE_MODEL")
        if not self.model:
            raise RuntimeError("OPENAI_IMAGE_MODEL not set")
        if _client is not None:
            self.client = _client
        else:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))

    def edit(self, *, reference_png: bytes, prompt: str, size: str = "1792x1024") -> ImageEditResult:
        """Call images.edit; return the first result's PNG bytes."""
        resp = self.client.images.edit(
            model=self.model,
            image=("clay.png", reference_png, "image/png"),
            prompt=prompt,
            size=size,
            n=1,
        )
        first = resp.data[0]
        png = _extract_png_bytes(first)
        return ImageEditResult(png_bytes=png, requested_size=size, model=self.model)


def _extract_png_bytes(datum: Any) -> bytes:
    """Handle both b64_json and url response shapes."""
    b64 = getattr(datum, "b64_json", None) or (datum.get("b64_json") if isinstance(datum, dict) else None)
    if b64:
        return base64.b64decode(b64)
    url = getattr(datum, "url", None) or (datum.get("url") if isinstance(datum, dict) else None)
    if url:
        import urllib.request
        with urllib.request.urlopen(url, timeout=60) as r:
            return r.read()
    raise RuntimeError(f"unknown image response shape: {datum!r}")


def crop_resize_to(png: bytes, target: tuple[int, int] = (1280, 720)) -> bytes:
    """Center-crop then resize `png` to exactly `target` (w, h). Preserves 16:9."""
    img = Image.open(io.BytesIO(png)).convert("RGB")
    tw, th = target
    sw, sh = img.size
    target_ratio = tw / th
    src_ratio = sw / sh
    if src_ratio > target_ratio:
        # too wide — crop sides
        new_w = int(sh * target_ratio)
        left = (sw - new_w) // 2
        box = (left, 0, left + new_w, sh)
    else:
        # too tall — crop top/bottom
        new_h = int(sw / target_ratio)
        top = (sh - new_h) // 2
        box = (0, top, sw, top + new_h)
    cropped = img.crop(box)
    resized = cropped.resize((tw, th), Image.LANCZOS)
    buf = io.BytesIO()
    resized.save(buf, "PNG")
    return buf.getvalue()
