from __future__ import annotations

import pytest

from image_worker.openai_client import OpenAIImageEditor, crop_resize_to


def test_edit_calls_client_with_model_and_size(tiny_png_bytes, fake_openai_factory):
    client = fake_openai_factory()
    editor = OpenAIImageEditor(_client=client)
    r = editor.edit(reference_png=tiny_png_bytes, prompt="x", size="1792x1024")
    assert r.model == "gpt-image-2.5-sunburst"
    assert r.requested_size == "1792x1024"
    assert client.calls[0]["model"] == "gpt-image-2.5-sunburst"
    assert client.calls[0]["size"] == "1792x1024"
    assert client.calls[0]["n"] == 1


def test_missing_model_env_raises(monkeypatch):
    monkeypatch.delenv("OPENAI_IMAGE_MODEL", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_IMAGE_MODEL"):
        OpenAIImageEditor(_client=object())


def test_crop_resize_widens(tiny_png_bytes):
    # Build a wider image (16:4) and resize to 16:9 — should center-crop vertically.
    from PIL import Image
    import io
    img = Image.new("RGB", (1600, 400), (0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    result = crop_resize_to(buf.getvalue(), target=(1280, 720))
    out = Image.open(io.BytesIO(result))
    assert out.size == (1280, 720)


def test_crop_resize_from_1792x1024_to_1280x720(tiny_png_bytes):
    from PIL import Image
    import io
    img = Image.new("RGB", (1792, 1024), (120, 120, 120))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    result = crop_resize_to(buf.getvalue(), target=(1280, 720))
    out = Image.open(io.BytesIO(result))
    assert out.size == (1280, 720)
