from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from extract.normalise import normalise, CLAUDE_LONG_SIDE_PX


def _write_image(tmp: Path, name: str, size=(1000, 600), color=(240, 240, 240)) -> Path:
    p = tmp / name
    Image.new("RGB", size, color).save(p)
    return p


def test_normalise_png_passthrough(tmp_path):
    p = _write_image(tmp_path, "plan.png")
    png, mime, info = normalise(p)
    assert mime == "image/png"
    assert info["input_format"] == ".png"
    assert len(png) > 0


def test_normalise_resizes_oversized_image(tmp_path):
    p = _write_image(tmp_path, "big.png", size=(8000, 4000))
    _png, _mime, info = normalise(p)
    long_side = max(info["pixels"])
    assert long_side == CLAUDE_LONG_SIDE_PX


def test_normalise_rejects_dwg(tmp_path):
    p = tmp_path / "f.dwg"
    p.write_bytes(b"not a real dwg")
    with pytest.raises(ValueError, match="DWG not supported"):
        normalise(p)


def test_normalise_rejects_unknown_ext(tmp_path):
    p = tmp_path / "f.bmp"
    p.write_bytes(b"nope")
    with pytest.raises(ValueError, match="unsupported"):
        normalise(p)


def test_normalise_pdf(tmp_path):
    """Create a tiny PDF via PyMuPDF so we don't need external fixtures."""
    import pymupdf  # type: ignore

    pdf = tmp_path / "plan.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=300)
    page.insert_text((20, 60), "FLOOR PLAN", fontsize=16)
    doc.save(pdf)
    doc.close()

    png, mime, info = normalise(pdf)
    assert mime == "image/png"
    assert info["input_format"] == ".pdf"
    assert info["page_count"] == 1
