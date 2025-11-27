# ============================================
# File: blog_src/scripts/cards/core/post_loader.py
# Load and sort blog posts from blog_src/content/posts
# ============================================

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable, List

import frontmatter

from .models import Post


# Корень всех постов внутри blog_src/
CONTENT_POSTS_ROOT = Path("blog_src/content/posts")

def _iter_markdown_files(root: Path) -> Iterable[Path]:
    """Находит все .md файлы в content/posts/**/**."""
    print("[cards][post_loader] === Сканирование markdown-файлов ===")
    print(f"[cards][post_loader] Поиск в директории: {root}")

    if not root.exists():
        print(f"[cards][post_loader][WARN] CONTENT_POSTS_ROOT не найден: {root}")
        return []

    md_files = sorted(root.rglob("*.md"))
    print(f"[cards][post_loader] Найдено markdown-файлов: {len(md_files)}")

    return md_files


def _parse_front_matter(md_path: Path) -> dict:
    """Парсер front matter для Hugo-постов."""
    print("[cards][post_loader] --- Парсим front matter ---")
    print(f"[cards][post_loader] Файл: {md_path}")

    try:
        fm_post = frontmatter.load(md_path)
    except Exception as e:
        print(f"[cards][post_loader][ERROR] Ошибка чтения YAML front matter: {md_path}")
        print(f"[cards][post_loader][ERROR] {e}")
        raise

    # slug теперь НЕ обязателен
    required_keys = ["title", "date"]

    for key in required_keys:
        if key not in fm_post:
            msg = f"В файле {md_path} отсутствует обязательное поле '{key}'"
            print(f"[cards][post_loader][ERROR] {msg}")
            raise ValueError(msg)

    raw_title = fm_post["title"]
    raw_date = fm_post["date"]

    title = str(raw_title).strip()

    # Автоматически берём slug из имени файла, если его нет
    if "slug" in fm_post and fm_post["slug"]:
        slug = str(fm_post["slug"]).strip()
    else:
        slug = md_path.stem  # имя файла без .md
        print(f"[cards][post_loader][INFO] slug отсутствует → используем имя файла: {slug}")

    print(f"[cards][post_loader] title   = {title!r}")
    print(f"[cards][post_loader] slug    = {slug!r}")
    print(f"[cards][post_loader] date_raw= {raw_date!r}")

    try:
        if isinstance(raw_date, datetime):
            date = raw_date
        else:
            date = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00"))
    except Exception as e:
        print(f"[cards][post_loader][ERROR] Невозможно преобразовать дату в datetime: {raw_date!r}")
        print(f"[cards][post_loader][ERROR] {e}")
        raise

    print(f"[cards][post_loader] Итоговая дата = {date.isoformat()}")

    meta = {"title": title, "slug": slug, "date": date}
    print("[cards][post_loader] Front matter успешно разобран.")
    return meta


def _build_post_from_meta(meta: dict, md_path: Path) -> Post:
    """Строит объект Post."""
    title = meta["title"]
    slug = meta["slug"]
    date = meta["date"]

    print(f"[cards][post_loader] Собираем Post: slug={slug!r}, date={date.isoformat()}")
    print(f"[cards][post_loader] source_path={md_path}")

    return Post(
        slug=slug,
        title=title,
        date=date,
        source_path=md_path,
    )


def load_all_posts() -> List[Post]:
    """Загружает все посты."""
    print("[cards][post_loader] === Старт загрузки всех постов ===")
    posts: List[Post] = []

    for md_path in _iter_markdown_files(CONTENT_POSTS_ROOT):
        print(f"[cards][post_loader] Обработка файла: {md_path}")
        try:
            meta = _parse_front_matter(md_path)
            post = _build_post_from_meta(meta, md_path)
            posts.append(post)
            print(f"[cards][post_loader] OK: {md_path} -> slug={post.slug!r}")
        except Exception as e:
            print(f"[cards][post_loader][ERROR] Ошибка при обработке {md_path}")
            print(f"[cards][post_loader][ERROR] {e}")
            raise

    print(f"[cards][post_loader] Всего загружено постов: {len(posts)}")
    return posts


def get_latest_posts(limit: int = 5) -> List[Post]:
    """Возвращает последние N постов по дате."""
    print(f"[cards][post_loader] === Получаем последние {limit} постов ===")
    all_posts = load_all_posts()

    if not all_posts:
        print("[cards][post_loader][WARN] Посты не найдены, возвращаем пустой список.")
        return []

    # Сортируем по дате (от новых к старым)
    all_posts.sort(key=lambda p: p.date, reverse=True)

    latest = all_posts[:limit]
    print(f"[cards][post_loader] Отобрано постов: {len(latest)}")

    for p in latest:
        print(f"[cards][post_loader]  - {p.date.isoformat()} | {p.slug!r}")

    return latest
