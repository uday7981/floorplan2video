"""File → PNG bytes. Handles PNG/JPG/WEBP/HEIC images, PDFs (page 1), and DXFs.

Returns (png_bytes, mime, info) where info is a dict useful for logging
(input format, page count, DXF layer names, etc.).

Keeps the long side ≤ MAX_LONG_SIDE_PX. For scans and photos, applies
Pillow's autocontrast; auto-deskew is NOT done at M1 (TODO(decision):
revisit in M5 when accuracy matters on real scans).
"""
from __future__ import annotations

import io
import logging
import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

# Register HEIF plugin with Pillow (idempotent).
try:
    import pillow_heif  # type: ignore
    pillow_heif.register_heif_opener()
except Exception:  # pragma: no cover
    pass

log = logging.getLogger(__name__)

MAX_LONG_SIDE_PX = 4096
CLAUDE_LONG_SIDE_PX = 2048  # TRD "PDF to 2048 px"; applied to all inputs for Claude
PDF_RENDER_DPI = 300

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".heic", ".heif"}


def normalise(path: Path) -> tuple[bytes, str, dict[str, Any]]:
    """Dispatch on file extension. Returns (png_bytes, mime, info)."""
    ext = path.suffix.lower()
    if ext in IMAGE_EXTS:
        return _normalise_image(path)
    if ext == ".pdf":
        return _normalise_pdf(path)
    if ext == ".dxf":
        return _normalise_dxf(path)
    if ext in (".dwg",):
        raise ValueError("DWG not supported; export as DXF and retry.")
    raise ValueError(f"unsupported file type: {ext}")


# ---------- images ----------

def _normalise_image(path: Path) -> tuple[bytes, str, dict[str, Any]]:
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)
    img = _rgb(img)
    img = ImageOps.autocontrast(img, cutoff=1)
    img = _resize_long(img, CLAUDE_LONG_SIDE_PX)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue(), "image/png", {"input_format": path.suffix.lower(), "pixels": img.size}


# ---------- PDFs ----------

def _normalise_pdf(path: Path) -> tuple[bytes, str, dict[str, Any]]:
    import pymupdf  # type: ignore

    doc = pymupdf.open(path)
    try:
        if doc.page_count < 1:
            raise ValueError("empty PDF")
        page = doc.load_page(0)
        # Scale factor from 72 dpi default to PDF_RENDER_DPI.
        mat = pymupdf.Matrix(PDF_RENDER_DPI / 72, PDF_RENDER_DPI / 72)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        img = _resize_long(img, CLAUDE_LONG_SIDE_PX)
        buf = io.BytesIO()
        img.save(buf, "PNG")
        return (
            buf.getvalue(),
            "image/png",
            {"input_format": ".pdf", "page_count": doc.page_count, "page_rendered": 1, "pixels": img.size},
        )
    finally:
        doc.close()


# ---------- DXF ----------

def _normalise_dxf(path: Path) -> tuple[bytes, str, dict[str, Any]]:
    """Rasterise the DXF modelspace. The TRD also wants direct geometry
    import via ezdxf — that is the fast path done in M5; here we just produce
    the review image so Claude can read room names.
    """
    import ezdxf  # type: ignore
    from ezdxf.addons.drawing import RenderContext, Frontend  # type: ignore
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend  # type: ignore
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    doc = ezdxf.readfile(str(path))
    msp = doc.modelspace()
    layers = [l.dxf.name for l in doc.layers]
    units = doc.header.get("$INSUNITS", 0)  # 0 = unitless; TRD asks user if unset

    fig, ax = plt.subplots(figsize=(16, 10), dpi=150)
    ax.set_axis_off()
    ctx = RenderContext(doc)
    out = MatplotlibBackend(ax)
    Frontend(ctx, out).draw_layout(msp, finalize=True)

    buf = io.BytesIO()
    plt.savefig(buf, format="PNG", bbox_inches="tight", pad_inches=0.0, dpi=150)
    plt.close(fig)
    buf.seek(0)

    img = Image.open(buf)
    img = _rgb(img)
    img = _resize_long(img, CLAUDE_LONG_SIDE_PX)
    out_buf = io.BytesIO()
    img.save(out_buf, "PNG")
    return (
        out_buf.getvalue(),
        "image/png",
        {"input_format": ".dxf", "layers": layers, "insunits": units, "pixels": img.size},
    )


# ---------- helpers ----------

def _rgb(img: Image.Image) -> Image.Image:
    return img.convert("RGB") if img.mode not in ("RGB",) else img


def _resize_long(img: Image.Image, long_side: int) -> Image.Image:
    w, h = img.size
    m = max(w, h)
    if m <= long_side:
        return img
    scale = long_side / m
    return img.resize((math.floor(w * scale), math.floor(h * scale)), Image.LANCZOS)
