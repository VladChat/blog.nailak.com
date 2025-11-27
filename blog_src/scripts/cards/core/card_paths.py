# ============================================
# File: scripts/cards/core/card_paths.py
# Resolve final card paths and existence
# ============================================

from __future__ import annotations

from pathlib import Path

from .models import PlatformConfig, Post

# Базовая директория контента для постов.
# Скрипт запускаем из blog_src/, поэтому контент лежит в content/posts.
CONTENT_ROOT = Path("content/posts")


def _get_post_dir(post: Post) -> Path:
    """
    Директория конкретного поста.

    ВАЖНО: для Nailak-проекта посты лежат так:
      content/posts/2025/10/<slug>.md

    То есть никакого уровня day и отдельной папки slug нет.
    Поэтому мы просто берём ПАПКУ, где лежит markdown-файл,
    и уже внутри неё создаём cards/<platform>/...
    """
    # Папка, в которой лежит файл поста
    return post.source_path.parent


def _build_card_path(config: PlatformConfig, post: Post, ensure_dirs: bool) -> Path:
    """
    Внутренняя функция, формирующая путь к карточке.

    Итоговый путь:
      <dir_of_md>/cards/<platform>/<slug>.jpg

    Пример для твоего кейса:
      content/posts/2025/10/cards/pinterest/kylie-jenner-....jpg
    """
    post_dir = _get_post_dir(post)
    platform_name = config.name

    cards_dir = post_dir / "cards" / platform_name
    if ensure_dirs:
        cards_dir.mkdir(parents=True, exist_ok=True)

    output_path = cards_dir / f"{post.slug}.jpg"
    print(f"[cards][paths] [{platform_name}] Итоговый путь карточки: {output_path}")
    return output_path


def get_output_path(config: PlatformConfig, post: Post) -> Path:
    """
    Возвращает путь для сохранения карточки и создаёт нужные директории,
    если их ещё нет.
    """
    return _build_card_path(config, post, ensure_dirs=True)


def card_exists(config: PlatformConfig, post: Post) -> bool:
    """
    Проверяет, существует ли карточка для поста на данной платформе.
    Директории при этом не создаёт.
    """
    path = _build_card_path(config, post, ensure_dirs=False)
    exists = path.is_file()
    if exists:
        print(f"[cards][paths] [{config.name}] Карточка уже существует: {path}")
    else:
        print(f"[cards][paths] [{config.name}] Карточка пока отсутствует: {path}")
    return exists
