# ============================================
# File: scripts/cards/core/models.py
# Base data models for posts and platforms
# ============================================

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol


@dataclass
class Post:
    """Представление одного поста блога, достаточное для генерации карточки."""
    slug: str
    title: str
    date: datetime
    # Полный путь к исходному .md файлу:
    #   blog_src/content/posts/<year>/<month>/<slug>.md
    source_path: Path


@dataclass
class PlatformConfig:
    """Конфигурация для конкретной платформы (Instagram, Facebook, Pinterest, ...).

    ВАЖНО:
      output_dir здесь носит скорее описательный характер.
      Реальный путь итоговой карточки строится динамически на основе:
        - post.source_path
        - имени платформы (config.name)
        и имеет вид:
        blog_src/content/posts/<year>/<month>/cards/<platform>/<slug>.jpg
    """
    name: str               # "instagram", "facebook", "pinterest", ...
    output_dir: str         # Информативно, в текущей схеме не используется напрямую
    template_dir: str       # Где лежат шаблоны, например "blog_src/static/social/templates/ig"
    image_width: int        # Ширина итогового изображения
    image_height: int       # Высота итогового изображения
    # Зона для заголовка: (x, y, width, height)
    title_zone: tuple[int, int, int, int]
    font_path: str | None = None  # Путь к TTF-шрифту
    font_size: int = 48           # Базовый размер шрифта для заголовка
    line_spacing: float = 1.2     # Межстрочный интервал (множитель)


class CardGenerator(Protocol):
    """Протокол для генератора карточки платформы."""

    def __call__(self, post: Post, template_path: str, output_path: str, config: PlatformConfig) -> None:
        ...


@dataclass
class Platform:
    """Полное описание платформы: конфиг + генератор."""
    config: PlatformConfig
    generator: CardGenerator
