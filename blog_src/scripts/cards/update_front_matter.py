# ============================================
# File: blog_src/scripts/cards/update_front_matter.py
# Purpose:
#   - Update front matter for posts that already
#     have generated social cards.
#   - Works specifically for NAILAK blog structure.
#
# Структура NAILAK:
#   Посты:
#     blog_src/content/posts/YYYY/MM/<slug>.md
#
#   Карточки:
#     blog_src/content/posts/YYYY/MM/cards/<platform>/<slug>.jpg
#
#   Публичные URL:
#     https://blog.nailak.com/posts/YYYY/MM/cards/<platform>/<slug>.jpg
# ============================================

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import frontmatter


# ============================================
# CONFIG — NAILAK
# ============================================

# Корень всех постов (Nailak)
CONTENT_ROOT = Path("blog_src/content/posts")

# Корень контента для построения относительных путей
CONTENT_BASE = Path("blog_src/content")

# Блог Nailak
BASE_URL = "https://blog.nailak.com"


# ============================================
# HELPERS
# ============================================

def find_all_posts() -> list[Path]:
    """Находит все .md файлы, кроме index.md, внутри CONTENT_ROOT."""
    posts: list[Path] = []

    if not CONTENT_ROOT.exists():
        print(f"[loader][WARN] CONTENT_ROOT не найден: {CONTENT_ROOT}")
        return posts

    for md_path in CONTENT_ROOT.rglob("*.md"):
        if md_path.name.lower() == "index.md":
            continue
        posts.append(md_path)

    posts = sorted(posts)
    print(f"[loader] Найдено markdown-файлов: {len(posts)}")

    return posts


def get_post_meta(md_path: Path) -> dict | None:
    """Читает front matter и возвращает slug/date/path/post."""

    try:
        post = frontmatter.load(md_path)
    except Exception as e:
        print(f"[frontmatter][ERROR] Cannot read {md_path}: {e}")
        return None

    # -----------------------------
    # SLUG: берём из front matter, если есть,
    # иначе автоматически из имени файла (stem)
    # -----------------------------
    slug = post.get("slug")
    if not slug:
        slug = md_path.stem
        print(f"[frontmatter] slug отсутствует → используем имя файла: {slug}")

    # -----------------------------
    # DATE (обязательное поле)
    # -----------------------------
    raw_date = post.get("date")
    if not raw_date:
        print(f"[frontmatter][WARN] Missing date: {md_path}")
        return None

    try:
        if isinstance(raw_date, datetime):
            date = raw_date
        else:
            # Поддержка ISO-формата и вариантов с 'Z'
            date = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00"))
    except Exception as e:
        print(f"[frontmatter][ERROR] Bad date format in {md_path}: {e}")
        return None

    return {
        "post": post,
        "slug": str(slug),
        "date": date,
        "path": md_path,
    }


def find_cards(meta: dict) -> dict | None:
    """
    Проверяет существование карточек:
      blog_src/content/posts/YYYY/MM/cards/<platform>/<slug>.jpg
    """

    year = f"{meta['date'].year:04d}"
    month = f"{meta['date'].month:02d}"
    slug = meta["slug"]

    base_dir = (
        CONTENT_ROOT
        / year
        / month
        / "cards"
    )

    platforms = ["facebook", "instagram", "pinterest"]

    card_paths = {
        p: base_dir / p / f"{slug}.jpg"
        for p in platforms
    }

    # Если нет хотя бы одной карточки — пропускаем этот пост
    for platform, path in card_paths.items():
        if not path.exists():
            print(f"[cards][WARN] No card for {platform}: {path}")
            return None

    print(f"[cards] Все карточки найдены для slug={slug}")
    return card_paths


def build_urls(card_paths: dict) -> dict:
    """
    Создаёт публичные URL на основе BASE_URL.

    Вход:
      path: blog_src/content/posts/YYYY/MM/cards/<platform>/<slug>.jpg

    Выход:
      https://blog.nailak.com/posts/YYYY/MM/cards/<platform>/<slug>.jpg
    """

    urls: dict[str, str] = {}

    for platform, path in card_paths.items():
        # Преобразуем абсолютный путь → путь относительно blog_src/content
        # blog_src/content/posts/...  →  posts/...
        rel = path.relative_to(CONTENT_BASE)
        public_url = f"{BASE_URL}/{rel.as_posix()}"
        urls[platform] = public_url

    # twitter = facebook
    urls["twitter"] = urls["facebook"]

    return urls


def update_frontmatter(meta: dict, card_urls: dict) -> None:
    """Обновляет front matter: добавляет/перезаписывает блок 'cards'."""

    post = meta["post"]
    md_path: Path = meta["path"]

    post["cards"] = {
        "facebook": card_urls["facebook"],
        "twitter": card_urls["twitter"],
        "instagram": card_urls["instagram"],
        "pinterest": card_urls["pinterest"],
    }

    # Сохраняем обратно в тот же файл
    with md_path.open("wb") as f:
        frontmatter.dump(post, f)

    print(f"[frontmatter][OK] Updated: {md_path}")


# ============================================
# MAIN
# ============================================

def process(latest_only: bool = False) -> None:
    posts = find_all_posts()

    if not posts:
        print("[system][WARN] No posts found")
        return

    # Режим обновления только самого "свежего" поста (по дате)
    if latest_only:
        print("[system] Обновляем только последний пост (по дате).")

        latest_meta: dict | None = None

        for md in posts:
            meta = get_post_meta(md)
            if not meta:
                continue

            if (latest_meta is None) or (meta["date"] > latest_meta["date"]):
                latest_meta = meta

        if latest_meta is None:
            print("[system][WARN] Не удалось определить последний пост (нет валидных дат).")
            return

        card_paths = find_cards(latest_meta)
        if not card_paths:
            print("[system][WARN] Для последнего поста карточки не найдены.")
            return

        card_urls = build_urls(card_paths)
        update_frontmatter(latest_meta, card_urls)
        return

    # Обновляем ВСЕ посты
    print("[system] Обновляем ВСЕ посты.")

    for md in posts:
        meta = get_post_meta(md)
        if not meta:
            continue

        card_paths = find_cards(meta)
        if not card_paths:
            continue

        card_urls = build_urls(card_paths)
        update_frontmatter(meta, card_urls)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--latest-only", action="store_true")
    args = parser.parse_args()

    process(latest_only=args.latest_only)
