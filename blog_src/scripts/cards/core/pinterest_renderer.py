# ============================================
# File: scripts/cards/core/pinterest_renderer.py
# Independent Pinterest renderer (separate from FB/IG)
# ============================================

from __future__ import annotations

from pathlib import Path
from typing import List

from PIL import Image, ImageDraw, ImageFont

from .models import PlatformConfig, Post


def _text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> tuple[int, int]:
    """Safe measurement using textbbox (Pillow 10+)"""
    if not text:
        return 0, 0
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _wrap_text(draw, text, font, max_width):
    """Soft-wrap text to fit width"""
    words = text.split()
    if not words:
        return []

    lines = []
    current = []

    for w in words:
        candidate = current + [w]
        line = " ".join(candidate)
        tw, _ = _text_size(draw, line, font)

        if tw <= max_width:
            current = candidate
        else:
            if current:
                lines.append(" ".join(current))
            current = [w]

    if current:
        lines.append(" ".join(current))

    return lines


# ==========================================================
# 🎯 MAIN Pinterest renderer — FULLY INDEPENDENT
# ==========================================================
def render_pinterest_title(
    template_path: Path,
    output_path: Path,
    post: Post,
    config: PlatformConfig,
):
    print(f"[cards][pinterest][render] Template: {template_path}")
    print(f"[cards][pinterest][render] Output:   {output_path}")

    img = Image.open(template_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    title = post.title
    x, y, w, h = config.title_zone

    # Pinterest-specific parameters
    padding = getattr(config, "bg_padding", 40)
    radius = getattr(config, "bg_radius", 40)
    bg_color = getattr(config, "bg_color", (255, 255, 255))
    base_font_size = config.font_size
    min_size = 26

    # Try decreasing font size until fits in vertical box
    size = base_font_size
    while True:
        font = ImageFont.truetype(config.font_path, size)
        lines = _wrap_text(draw, title, font, w)

        line_heights = [_text_size(draw, line, font)[1] for line in lines]
        total_text_h = sum(line_heights) * config.line_spacing

        if total_text_h <= h or size <= min_size:
            break
        size -= 2

    # Build final lines
    font = ImageFont.truetype(config.font_path, size)
    lines = _wrap_text(draw, title, font, w)
    line_heights = [_text_size(draw, line, font)[1] for line in lines]
    text_height = sum(line_heights) * config.line_spacing

    # Compute background box
    bg_left = x
    bg_top = y
    bg_right = x + w
    bg_bottom = y + text_height + padding * 2

    # White rounded rectangle
    draw.rounded_rectangle(
        [bg_left, bg_top, bg_right, bg_bottom],
        radius=radius,
        fill=bg_color,
    )

    # Draw text
    color = (230, 70, 20)
    cur_y = bg_top + padding
    text_x = bg_left + padding

    for line, lh in zip(lines, line_heights):
        draw.text((text_x, cur_y), line, font=font, fill=color)
        cur_y += lh * config.line_spacing

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, quality=95)

    print(f"[cards][pinterest][render] Saved: {output_path}")
