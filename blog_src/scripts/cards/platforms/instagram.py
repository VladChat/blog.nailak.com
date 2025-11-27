# ============================================
# File: scripts/cards/platforms/instagram.py
# Instagram card configuration and generator
# ============================================

from __future__ import annotations

from pathlib import Path
from typing import List

from PIL import Image, ImageDraw, ImageFont

from ..core.models import PlatformConfig, Platform, Post


# Конфиг платформы (нужен для registry/card_paths/template_manager)
INSTAGRAM_CONFIG = PlatformConfig(
    name="instagram",
    output_dir="content/posts/*/cards/instagram",
    template_dir="static/social/templates/ig",
    image_width=1080,
    image_height=1350,

    # Здесь просто держим базовую зону текста; реальный рендер ниже
    # (x, y, w, h) — внутри верхней белой полосы
    title_zone=(60, 40, 960, 240),

    font_path="static/social/fonts/BungeeSpice-Regular.ttf",
    font_size=72,
    line_spacing=1.2,
)


# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ТОЛЬКО ДЛЯ INSTAGRAM =====

def _ig_text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> tuple[int, int]:
    """Измерение текста через textbbox (Pillow >= 10)."""
    if not text:
        return 0, 0
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    return w, h


def _ig_wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
    """Перенос строк под max_width для Instagram."""
    words = text.split()
    if not words:
        return []

    lines: List[str] = []
    current: List[str] = []

    for w in words:
        candidate = current + [w]
        line = " ".join(candidate)
        lw, _ = _ig_text_size(draw, line, font)
        if lw <= max_width:
            current = candidate
        else:
            if current:
                lines.append(" ".join(current))
            current = [w]

    if current:
        lines.append(" ".join(current))

    return lines


# ===== ОСНОВНОЙ РЕНДЕР ДЛЯ INSTAGRAM =====

def instagram_generator(post: Post, template_path: str, output_path: str, config: PlatformConfig) -> None:
    """
    Рендер Instagram-карточки:
      - белая шапка сверху фиксированной высоты,
      - внутри шапки — текст с отступами,
      - шрифт подбирается под высоту и ширину.
    """

    print(f"[cards][instagram] Генерация карточки для поста {post.slug!r}")
    print(f"[cards][instagram] Шаблон: {template_path}")
    print(f"[cards][instagram] Выход: {output_path}")

    img = Image.open(template_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    title = post.title

    # ----- Геометрия шапки -----
    img_w, img_h = img.size               # ожидаем 1080x1350
    header_height = 320                   # высота белой шапки (полностью в верхней белой зоне)
    header_top = 0
    header_left = 0
    header_right = img_w
    header_bottom = header_top + header_height

    # Внутренние отступы
    padding_x = 60    # слева/справа
    padding_y = 40    # сверху/снизу

    inner_left = header_left + padding_x
    inner_right = header_right - padding_x
    inner_top = header_top + padding_y
    inner_bottom = header_bottom - padding_y

    inner_width = inner_right - inner_left
    inner_height = inner_bottom - inner_top

    # ----- Подбор размера шрифта -----
    size = config.font_size
    min_size = 26

    while True:
        font = ImageFont.truetype(config.font_path, size)
        lines = _ig_wrap_text(draw, title, font, inner_width)

        line_heights = [_ig_text_size(draw, line, font)[1] for line in lines]
        total_h = sum(line_heights) * config.line_spacing

        if total_h <= inner_height or size <= min_size:
            break

        size -= 2

    # Финальный пересчёт
    font = ImageFont.truetype(config.font_path, size)
    lines = _ig_wrap_text(draw, title, font, inner_width)
    line_heights = [_ig_text_size(draw, line, font)[1] for line in lines]
    total_h = sum(line_heights) * config.line_spacing

    # ----- Белая шапка (на случай будущих шаблонов) -----
    # Сейчас шапка совпадает с существующей белой зоной, так что её не видно.
    draw.rectangle(
        [header_left, header_top, header_right, header_bottom],
        fill=(255, 255, 255)
    )

    # ----- Рисуем текст внутри шапки с паддингами -----
    text_x = inner_left
    text_y = inner_top + (inner_height - total_h) / 2  # вертикальное центрирование

    text_color = (230, 70, 20)

    for line, h_line in zip(lines, line_heights):
        draw.text((text_x, text_y), line, font=font, fill=text_color)
        text_y += h_line * config.line_spacing

    # ----- Сохраняем -----
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, quality=95)

    print(f"[cards][instagram] Готово: {out_path}")


INSTAGRAM_PLATFORM = Platform(
    config=INSTAGRAM_CONFIG,
    generator=instagram_generator,
)
