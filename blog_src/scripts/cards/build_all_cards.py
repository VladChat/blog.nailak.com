# ============================================
# File: scripts/cards/build_all_cards.py
# Orchestrate card generation for ALL posts
# ============================================

from __future__ import annotations

from pathlib import Path

from .core.post_loader import get_latest_posts
from .core.registry import get_platforms
from .core.card_paths import card_exists, get_output_path
from .core.template_manager import get_next_template


def ensure_output_dir(path: Path) -> None:
    """Создаёт директорию для итогового файла, если её ещё нет."""
    parent = path.parent
    if not parent.exists():
        print(f"[cards][build] Создаём директорию: {parent}")
        parent.mkdir(parents=True, exist_ok=True)


def build_all_cards(limit_posts: int | None = None) -> None:
    """Основной сценарий:
      - берём ВСЕ посты (лимит отключён),
      - для каждой зарегистрированной платформы проверяем наличие карточки,
      - если карточки нет — выбираем шаблон и генерируем.

    Карточки сохраняются по схеме:
      blog_src/content/posts/<year>/<month>/<day>/<slug>/cards/<platform>/<slug>.jpg
    """

    print("[cards][build] === Старт генерации карточек для ВСЕХ постов ===")

    # Получаем все посты: limit=None → значит "все"
    posts = get_latest_posts(limit=None)
    platforms = get_platforms()

    if not posts:
        print("[cards][build] Нет постов для обработки, выходим.")
        return

    platform_names = [p.config.name for p in platforms]
    print(f"[cards][build] Зарегистрированные платформы: {platform_names}")
    print(f"[cards][build] Найдено постов: {len(posts)}")

    for post in posts:
        print(f"[cards][build] --- Обработка поста: {post.slug!r} | {post.date.isoformat()} ---")
        print(f"[cards][build] source_path: {post.source_path}")

        for platform in platforms:
            cfg = platform.config
            platform_name = cfg.name

            out_path = get_output_path(cfg, post)

            if card_exists(cfg, post):
                print(f"[cards][build] [{platform_name}] Карточка уже существует, пропускаем: {out_path}")
                continue

            # Выбираем шаблон для платформы
            template_path = get_next_template(cfg)
            print(f"[cards][build] [{platform_name}] Выбран шаблон: {template_path}")

            ensure_output_dir(out_path)

            print(f"[cards][build] [{platform_name}] Создаём карточку → {out_path}")

            platform.generator(
                post=post,
                template_path=str(template_path),
                output_path=str(out_path),
                config=cfg,
            )

    print("[cards][build] === Генерация карточек завершена ===")


if __name__ == "__main__":
    # Запуск без лимита: генерируем карточки для ВСЕХ постов
    build_all_cards(limit_posts=None)
