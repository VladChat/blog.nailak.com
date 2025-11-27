# ============================================
# File: blog_src/scripts/cards/update_front_matter.py
# Purpose:
#   - Update front matter for posts that already
#     have generated social cards.
#   - Works specifically for NAILAK blog structure.
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

# Блог Nailak
BASE_URL = "https://blog.nailak.com"


# ============================================
# HELPERS
# ============================================

def find_all_posts() -> list[Path]:
    """Находит все .md файлы, кроме index.md, в CONTENT_ROOT."""
    if not CONTENT_ROOT.exists():
        print(f"[loader][ERROR] CONTENT_ROOT не найден: {CONTENT_ROOT}")
        return []

    posts: list[Path] = []
    for md_path in CONTENT_ROOT.rglob("*.md"):
        if md_path.name.lower() == "index.md":
            continue
        posts.append(md_path)

    posts = sorted(posts)
    print(f"[loader] Найдено markdown-файлов: {len(posts)}")
    return posts


def get_post_meta(md_path: Path) -> dict | None:
    """Читает front matter и возвращает slug/date/path/post."""

    print(f"[frontmatter] Обработка файла: {md_path}")

    try:
        post = frontmatter.load(md_path)
    except Exception as e:
        print(f"[frontmatter][ERROR] Cannot read {md_path}: {e}")
        return None

    # -----------------------------
    # SLUG: если нет в FM — берём из имени файла
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
        if isinstance(raw_date, datetime):
            date_val = raw_date
        else:
            # Приводим к ISO, заменяем Z → +00:00
            date_val = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00"))
    except Exception as e:
        print(f"[frontmatter][ERROR] Bad date format in {md_path}: {e}")
        return None

    print(
        f"[frontmatter] title={post.get('title')!r}, "
        f"slug={slug!r}, date={date_val.isoformat()}"
    )

    return {
        "post": post,
        "slug": slug,
        "date": date_val,
        "path": md_path,
    }


def load_all_meta() -> list[dict]:
    """Загружает метаданные для всех постов."""
    posts = find_all_posts()
    metas: list[dict] = []

    for md in posts:
        meta = get_post_meta(md)
        if meta:
            metas.append(meta)

    print(f"[system] Загружено метаданных: {len(metas)}")
    return metas


def find_cards(meta: dict) -> dict | None:
    """
    Ищет карточки для поста, поддерживая две возможные схемы путей:

    1) Текущая (упрощённая, как в логах генератора):
       blog_src/content/posts/YYYY/MM/cards/<platform>/<slug>.jpg

    2) Более вложенная (на будущее / совместимость):
       blog_src/content/posts/YYYY/MM/DD/slug/cards/<platform>/<slug>.jpg
    """

    date_val: datetime = meta["date"]
    slug: str = meta["slug"]

    year = f"{date_val.year:04d}"
    month = f"{date_val.month:02d}"
    day = f"{date_val.day:02d}"

    # Порядок важен только для логики Twitter fallback (facebook → instagram → pinterest)
    platforms = ["facebook", "instagram", "pinterest"]

    base_dirs = [
        # Вариант 1 — как сейчас создаются карточки:
        # blog_src/content/posts/YYYY/MM/cards/...
        CONTENT_ROOT / year / month / "cards",

        # Вариант 2 — более вложенная структура:
        # blog_src/content/posts/YYYY/MM/DD/slug/cards/...
        CONTENT_ROOT / year / month / day / slug / "cards",
    ]

    card_paths: dict[str, Path] = {}

    for platform in platforms:
        found_path = None

        for base_dir in base_dirs:
            candidate = base_dir / platform / f"{slug}.jpg"
            if candidate.exists():
                found_path = candidate
                break

        if found_path:
            card_paths[platform] = found_path
            print(f"[cards] Найдена карточка для {platform}: {found_path}")
        else:
            # Логируем, но НЕ падаем — просто этой платформы нет
            print(
                f"[cards][WARN] Не найдена карточка для {platform}: "
                f"пробовал {', '.join(str(b / platform / (slug + '.jpg')) for b in base_dirs)}"
            )

    if not card_paths:
        print(f"[cards][WARN] Ни одной карточки не найдено для slug={slug}")
        return None

    print(f"[cards] Всего платформ с карточками для slug={slug}: {len(card_paths)}")
    return card_paths


def build_urls(card_paths: dict[str, Path]) -> dict[str, str]:
    """Создаёт публичные URL на основе BASE_URL.

    Файлы лежат под blog_src/content/...,
    публичный путь = путь относительно 'blog_src/content':
      blog_src/content/posts/... → /posts/...
    """

    urls: dict[str, str] = {}

    for platform, path in card_paths.items():
        try:
            rel = path.relative_to(Path("blog_src/content"))
        except ValueError:
            # fallback (не должно срабатывать в норме)
            rel = path

        public_url = f"{BASE_URL}/{rel.as_posix()}"
        urls[platform] = public_url
        print(f"[urls] {platform}: {public_url}")

    # Twitter fallback: facebook → instagram → pinterest
    twitter_url = (
        urls.get("facebook")
        or urls.get("instagram")
        or urls.get("pinterest")
    )

    if twitter_url:
        urls["twitter"] = twitter_url
        print(f"[urls] twitter: {twitter_url} (fallback)")

    return urls


def update_frontmatter(meta: dict, card_urls: dict[str, str]) -> None:
    """Обновляет front matter: добавляет/обновляет блок cards."""

    post = meta["post"]
    md_path = meta["path"]

    # Существующий блок cards (если был) не теряем — обновляем/дополняем
    existing_cards = post.get("cards", {})
    existing_cards.update(card_urls)

    post["cards"] = existing_cards

    with md_path.open("wb") as f:
        frontmatter.dump(post, f)

    print(f"[frontmatter][OK] Updated: {md_path}")


# ============================================
# MAIN
# ============================================

def process(latest_only: bool = False) -> None:
    metas = load_all_meta()

    if not metas:
        print("[system][WARN] No posts found (meta)")
        return

    if latest_only:
        # Берём пост с самой поздней датой
        metas.sort(key=lambda m: m["date"])
        target = [metas[-1]]
        print(f"[system] Обновляем только последний по дате пост: {target[0]['path']}")
    else:
        target = metas
        print(f"[system] Обновляем ВСЕ посты: {len(target)} шт.")

    for meta in target:
        card_paths = find_cards(meta)
        if not card_paths:
            continue

        card_urls = build_urls(card_paths)
        if not card_urls:
            continue

        update_frontmatter(meta, card_urls)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--latest-only", action="store_true")
    args = parser.parse_args()

    process(latest_only=args.latest_only)
