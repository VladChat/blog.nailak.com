# ============================================
# File: scripts/cards/core/text_renderer.py
# Draw wrapped title text on image template
# ============================================

from __future__ import annotations

from pathlib import Path
from typing import List

from PIL import Image, ImageDraw, ImageFont

from .models import PlatformConfig, Post


def _text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> tuple[int, int]:
    """
    Pillow >= 10 безопасный способ измерить размеры текста через textbbox().
    """
    if not text:
        return 0, 0
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    return w, h


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
    """
    Разбиваем текст на строки так, чтобы они помещались по ширине (max_width).
    """
    words = text.split()
    if not words:
        return []

    lines: List[str] = []
    current: List[str] = []

    for w in words:
        candidate = current + [w]
        line = " ".join(candidate)
        line_w, _ = _text_size(draw, line, font)

        if line_w <= max_width:
            current = candidate
        else:
            if current:
                lines.append(" ".join(current))
            current = [w]

    if current:
        lines.append(" ".join(current))

    return lines


def render_title_on_template(
    template_path: Path,
    output_path: Path,
    post: Post,
    config: PlatformConfig,
) -> None:

    print(f"[cards][text] Template: {template_path}")
    print(f"[cards][text] Output  : {output_path}")
    print(f"[cards][text] Title   : {post.title!r}")

    img = Image.open(template_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Эта зона теперь используется ТОЛЬКО для расчётов ширины текста.
    x, y, w, h = config.title_zone
    title = post.title

    # Параметры для Facebook
    padding_x = 60      # слева/справа
    padding_y = 60      # сверху/снизу
    offset_from_top = 60
    corner_radius = 40

    # Подбор размера шрифта
    size = config.font_size
    min_size = 26

    while True:
        font = ImageFont.truetype(config.font_path, size)
        lines = _wrap_text(draw, title, font, w)

        line_heights = [_text_size(draw, line, font)[1] for line in lines]
        total_h = sum(line_heights) * config.line_spacing

        if total_h <= h or size <= min_size:
            break

        size -= 2

    # Финальные параметры
    font = ImageFont.truetype(config.font_path, size)
    lines = _wrap_text(draw, title, font, w)
    line_heights = [_text_size(draw, line, font)[1] for line in lines]
    text_height = sum(line_heights) * config.line_spacing

    # Координаты белой подложки (динамическая высота)
    box_left = padding_x
    box_top = offset_from_top
    box_right = img.width - padding_x
    box_bottom = box_top + text_height + padding_y * 2

    # ---------------------------------------------------
    # Белая ПОЛНОСТЬЮ непрозрачная плашка с закруглёнными углами
    # ---------------------------------------------------
    if config.name == "facebook":
        draw.rounded_rectangle(
            [box_left, box_top, box_right, box_bottom],
            radius=corner_radius,
            fill=(255, 255, 255)
        )

    # ---------------------------------------------------
    # Рисуем текст
    # ---------------------------------------------------
    text_x = box_left + padding_x
    cur_y = box_top + padding_y
    text_color = (230, 70, 20)

    for line, h_line in zip(lines, line_heights):
        draw.text((text_x, cur_y), line, font=font, fill=text_color)
        cur_y += h_line * config.line_spacing

    # Сохраняем
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, quality=95)

    print(f"[cards][text] Карточка сохранена: {output_path}")
