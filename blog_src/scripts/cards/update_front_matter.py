# ============================================
# File: blog_src/scripts/cards/update_front_matter.py
# Purpose: Inject social card URLs into Markdown front matter
# Now updates ALL posts (limit removed)
# ============================================

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Optional

import frontmatter

CONTENT_ROOT = Path("blog_src/content/posts")
BASE_URL = "https://blog.equalle.com"


# ========= helpers =========

def _parse_date_value(raw) -> Optional[datetime]:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except Exception:
        return None


# ========= поиск постов и дат =========

def find_all_md_posts() -> List[Path]:
    return [
        p for p in CONTENT_ROOT.rglob("*.md")
        if p.name != "index.md"
    ]


def parse_post_date(md_path: Path) -> Optional[datetime]:
    try:
        fm = frontmatter.load(md_path)
    except Exception:
        return None
    return _parse_date_value(fm.get("date"))


# ========= работа с карточками =========

def _cards_root_for(slug: str, date: datetime) -> Path:
    y = f"{date.year:04d}"
    m = f"{date.month:02d}"
    d = f"{date.day:02d}"
    return CONTENT_ROOT / y / m / d / slug / "cards"


def cards_exist(slug: str, date: datetime) -> bool:
    cards_root = _cards_root_for(slug, date)
    needed = [
        cards_root / "facebook" / f"{slug}.jpg",
        cards_root / "instagram" / f"{slug}.jpg",
        cards_root / "pinterest" / f"{slug}.jpg",
    ]
    return all(p.exists() for p in needed)


def build_card_urls(slug: str, date: datetime) -> dict:
    cards_root = _cards_root_for(slug, date)

    rel_cards = cards_root.relative_to(CONTENT_ROOT.parent).as_posix()
    rel_cards = "/" + rel_cards

    full = f"{BASE_URL}{rel_cards}"

    return {
        "facebook":  f"{full}/facebook/{slug}.jpg",
        "twitter":   f"{full}/facebook/{slug}.jpg",
        "instagram": f"{full}/instagram/{slug}.jpg",
        "pinterest": f"{full}/pinterest/{slug}.jpg",
    }


# ========= обновление front matter =========

def update_front_matter(md_path: Path):
    post = frontmatter.load(md_path)

    slug = post.metadata.get("slug")
    if not slug:
        print(f"[skip] No slug in {md_path}")
        return

    date = _parse_date_value(post.metadata.get("date"))
    if not date:
        print(f"[skip] No valid date in {md_path}")
        return

    if not cards_exist(slug, date):
        print(f"[skip] No cards for {slug}")
        return

    post.metadata["cards"] = build_card_urls(slug, date)

    # FIX: open in BINARY MODE ("wb")
    with md_path.open("wb") as f:
        frontmatter.dump(post, f)

    print(f"[update] Added cards: {slug}")


# ========= main =========

def main():
    posts = find_all_md_posts()
    print(f"[info] Found {len(posts)} markdown posts")

    dated: List[tuple[datetime, Path]] = []
    for md in posts:
        dt = parse_post_date(md)
        if dt:
            dated.append((dt, md))

    dated.sort(key=lambda x: x[0], reverse=True)

    all_posts = [md for _, md in dated]

    print("[info] Updating ALL posts:")
    for p in all_posts:
        print(" -", p)

    for md in all_posts:
        update_front_matter(md)


if __name__ == "__main__":
    main()
