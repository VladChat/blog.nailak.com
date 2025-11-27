# ============================================
# File: blog_src/scripts/cards/update_front_matter.py
# Purpose:
#   - Update front matter for posts that already
#     have generated social cards.
#   - Works specifically for NAILAK blog structure.
# ============================================

from __future__ import annotations

import argparse
from pathlib import Path
import frontmatter
from datetime import datetime


# ============================================
# CONFIG — NAILAK
# ============================================

# Корень всех постов (Nailak)
CONTENT_ROOT = Path("blog_src/content/posts")

# Блог Nailak
BASE_URL = "https://blog.nailak.com"


# ============================================
# HELPERS
# ============================================

def find_all_posts():
    """Находит все .md файлы, кроме index.md."""
    posts = []

    for md_path in CONTENT_ROOT.rglob("*.md"):
        if md_path.name.lower() == "index.md":
            continue
        posts.append(md_path)

    posts = sorted(posts)
    print(f"[loader] Найдено markdown-файлов: {len(posts)}")

    return posts


def get_post_meta(md_path: Path):
    """Читает front matter и slug/date."""

    try:
        post = frontmatter.load(md_path)
    except Exception as e:
        print(f"[frontmatter][ERROR] Cannot read {md_path}: {e}")
        return None

    # -----------------------------
    # SLUG: берем автоматически из имени файла
    # -----------------------------
    slug = post.get("slug")
    if not slug:
        slug = md_path.stem
        print(f"[frontmatter] slug отсутствует → используем имя файла: {slug}")

    # -----------------------------
    # DATE
    # -----------------------------
    raw_date = post.get("date")
    if not raw_date:
        print(f"[frontmatter][WARN] Missing date: {md_path}")
        return None

    try:
        if not isinstance(raw_date, datetime):
            raw_date = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00"))
    except Exception as e:
        print(f"[frontmatter][ERROR] Bad date format in {md_path}: {e}")
        return None

    return {
        "post": post,
        "slug": slug,
        "date": raw_date,
        "path": md_path,
    }


def find_cards(meta: dict):
    """
    Проверяет существование карточек:
    blog_src/content/posts/YYYY/MM/DD/slug/cards/<platform>/<slug>.jpg
    """

    year = f"{meta['date'].year:04d}"
    month = f"{meta['date'].month:02d}"
    day = f"{meta['date'].day:02d}"
    slug = meta["slug"]

    base_dir = (
        CONTENT_ROOT
        / year
        / month
        / day
        / slug
        / "cards"
    )

    platforms = ["facebook", "instagram", "pinterest"]

    card_paths = {
        p: base_dir / p / f"{slug}.jpg"
        for p in platforms
    }

    # Если нет хотя бы одной карточки — пропускаем
    for p, path in card_paths.items():
        if not path.exists():
            print(f"[cards][WARN] No card for {p}: {path}")
            return None

    print(f"[cards] Все карточки найдены для slug={slug}")
    return card_paths


def build_urls(card_paths: dict):
    """Создаёт публичные URL на основе BASE_URL."""

    urls = {}

    for platform, path in card_paths.items():
        # Преобразуем абсолютный путь → путь относительно blog_src/
        rel = path.relative_to(Path("blog_src"))
        public_url = f"{BASE_URL}/{rel.as_posix()}"
        urls[platform] = public_url

    # twitter = facebook
    urls["twitter"] = urls["facebook"]

    return urls


def update_frontmatter(meta: dict, card_urls: dict):
    """Обновляет front matter."""

    post = meta["post"]
    md_path = meta["path"]

    post["cards"] = {
        "facebook": card_urls["facebook"],
        "twitter": card_urls["twitter"],
        "instagram": card_urls["instagram"],
        "pinterest": card_urls["pinterest"],
    }

    with md_path.open("wb") as f:
        frontmatter.dump(post, f)

    print(f"[frontmatter][OK] Updated: {md_path}")


# ============================================
# MAIN
# ============================================

def process(latest_only: bool = False):
    posts = find_all_posts()

    if not posts:
        print("[system][WARN] No posts found")
        return

    if latest_only:
        target = [posts[-1]]
        print("[system] Обновляем только последний пост.")
    else:
        target = posts
        print("[system] Обновляем ВСЕ посты.")

    for md in target:
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
