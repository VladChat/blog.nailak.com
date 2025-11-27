# ============================================
# File: scripts/cards/platforms/pinterest.py
# Pinterest card configuration + generator
# ============================================

from __future__ import annotations

from pathlib import Path

from ..core.models import PlatformConfig, Platform, Post
from ..core.pinterest_renderer import render_pinterest_title


PINTEREST_CONFIG = PlatformConfig(
    name="pinterest",
    output_dir="content/posts/*/cards/pinterest",
    template_dir="static/social/templates/pn",

    image_width=1000,
    image_height=1500,

    # UPDATED title_zone — wider & higher
    title_zone=(30, 20, 940, 420),

    font_path="static/social/fonts/BungeeSpice-Regular.ttf",
    font_size=72,
    line_spacing=1.2,
)


def pinterest_generator(post: Post, template_path: str, output_path: str, config: PlatformConfig):
    print(f"[cards][pinterest] Генерация карточки: {post.slug}")

    render_pinterest_title(
        template_path=Path(template_path),
        output_path=Path(output_path),
        post=post,
        config=config,
    )


PINTEREST_PLATFORM = Platform(
    config=PINTEREST_CONFIG,
    generator=pinterest_generator,
)
