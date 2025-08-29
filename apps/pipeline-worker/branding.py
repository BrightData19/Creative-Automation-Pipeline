from __future__ import annotations

from typing import Tuple
from PIL import Image


def overlay_logo(
    base: Image.Image,
    logo: Image.Image,
    position: str = "top_right",
    max_width_ratio: float = 0.12,
    edge_padding_ratio: float = 0.06,
    opacity: float = 0.95,
) -> Image.Image:
    """Overlay a logo onto the base image with safe-area padding.

    - Ensures the logo occupies up to max_width_ratio of the base width.
    - Keeps at least edge_padding_ratio margins from edges.
    - Positions: top_left, top_right, bottom_left, bottom_right.
    """
    base = base.convert("RGBA")
    logo = logo.convert("RGBA")

    bw, bh = base.size
    target_w = int(bw * max_width_ratio)
    scale = target_w / logo.width
    target_h = int(logo.height * scale)
    logo_resized = logo.resize((target_w, target_h), Image.Resampling.LANCZOS)

    # Apply opacity
    if opacity < 1.0:
        alpha = logo_resized.split()[3]
        alpha = alpha.point(lambda p: int(p * opacity))
        logo_resized.putalpha(alpha)

    pad = int(bw * edge_padding_ratio)
    lw, lh = logo_resized.size
    if position == "top_left":
        x, y = pad, pad
    elif position == "top_right":
        x, y = bw - lw - pad, pad
    elif position == "bottom_left":
        x, y = pad, bh - lh - pad
    else:  # bottom_right
        x, y = bw - lw - pad, bh - lh - pad

    out = base.copy()
    out.alpha_composite(logo_resized, (x, y))
    return out.convert("RGB")

