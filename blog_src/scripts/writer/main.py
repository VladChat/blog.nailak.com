# blog_src/scripts/writer/main.py
import json
from datetime import datetime, timezone
from pathlib import Path

from . import llm
from . import posts
from .rss_fetch import get_latest_topic
from .config_loader import load_writer_config

DATA_DIR = Path("blog_src/data")
KEYWORDS_FILE = DATA_DIR / "keywords.json"
STATE_FILE = DATA_DIR / "state.json"
CONTENT_DIR = Path("blog_src/content/posts")


def load_prompt_template() -> str:
    with open("blog_src/config/prompt_template.txt", "r", encoding="utf-8") as f:
        return f.read()


def load_keywords() -> list:
    with open(KEYWORDS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_state() -> dict:
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"keyword_index": 0, "seen": []}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def build_prompt(topic: str, summary: str, original_url: str | None = None) -> str:
    """
    Собирает текст промпта.
    Если обнаружен URL оригинального источника — вставляем 'Original source: <url>' в блок topic.
    """
    template = load_prompt_template()
    topic_block = topic
    if original_url:
        topic_block = f"{topic_block}\n\nOriginal source: {original_url}"
    if summary:
        topic_block = f"{topic_block}\n\nContext: {summary}"
    else:
        topic_block = f"{topic_block}\n\nContext: "
    return template.format(topic=topic_block)


def _norm_tag(s: str) -> str:
    """
    Нормализация строки под тег: латиница/цифры, дефисы вместо прочих символов,
    урезание подряд идущих дефисов, обрезка до разумной длины.
    """
    s = (s or "").strip().lower()
    if not s:
        return ""
    out = []
    prev_dash = False
    for ch in s:
        if ch.isalnum():
            out.append(ch)
            prev_dash = False
        else:
            if not prev_dash:
                out.append("-")
                prev_dash = True
    t = "".join(out).strip("-")
    if not t:
        return ""
    while "--" in t:
        t = t.replace("--", "-")
    return t[:40]


def _extract_secondary_from_article(md_text: str) -> str:
    """
    Пытается вытащить 1 осмысленный тематический тег из сгенерированного текста статьи.
    Ищем по белому списку доменных ключей, чтобы не цеплять случайные слова.
    Возвращаем НОРМАЛИЗОВАННЫЙ тег (для front-matter).
    """
    if not md_text:
        return ""
    candidates = [
        "glp-1", "ozempic", "semaglutide",
        "manicure", "nail polish", "cuticle oil",
        "strength training", "workout", "fitness", "wellness",
    ]
    text_low = md_text.lower()
    for c in candidates:
        if c in text_low:
            return _norm_tag(c)
    return ""


def _extract_secondary_from_topic(topic: str) -> str:
    """
    Фоллбэк: пытается вытащить 1 тематический тег из заголовка RSS/топика,
    если в тексте статьи ничего не нашли.
    """
    if not topic:
        return ""
    # Простая эвристика + небольшой whitelisting
    tokens = [t for t in topic.lower().replace("—", " ").replace("-", " ").split() if len(t) > 2]
    white = {
        "glp", "glp1", "glp-1", "ozempic", "semaglutide",
        "manicure", "nail", "polish", "cuticle", "oil",
        "workout", "fitness", "wellness", "training", "strength",
    }
    for t in tokens:
        if t in white:
            return _norm_tag(t)
    # Если вообще ничего — попробуем первый “содержательный” токен
    for t in tokens:
        if t.isalpha():
            return _norm_tag(t)
    return ""


def main():
    cfg = load_writer_config()

    # 1️⃣ Получаем данные из RSS (теперь три значения)
    topic, summary, original_url = get_latest_topic()
    topic = topic or "Travel update"
    summary = summary or ""
    original_url = original_url or None

    # 🧾 Логирование RSS и финального topic-context
    print("───────────────────────────────")
    print("📰 Extracted from RSS:")
    print(f"Title: {topic}")
    if summary:
        print(f"Summary: {summary[:400]}{'...' if len(summary) > 400 else ''}")
    else:
        print("Summary: (no summary provided)")
    print(f"Original source: {original_url if original_url else '(not detected)'}")
    print()

    topic_context_str = topic
    if original_url:
        topic_context_str += f"\n\nOriginal source: {original_url}"
    topic_context_str += f"\n\nContext: {summary}"

    print("🧩 Final topic-context sent to GPT:")
    print(topic_context_str[:600] + ("..." if len(topic_context_str) > 600 else ""))
    print("───────────────────────────────")

    # 2️⃣ Ключевые слова и состояние
    try:
        keywords = load_keywords()
    except Exception as e:
        print(f"⚠️ Could not load keywords.json: {e}")
        keywords = []

    state = load_state()
    idx = max(0, int(state.get("keyword_index", 0)))
    if keywords:
        if idx >= len(keywords):
            idx = 0
        keyword = (keywords[idx] or "").strip()
    else:
        keyword = ""

    # 3️⃣ Формируем промпт
    prompt = build_prompt(topic, summary, original_url)

    # 4️⃣ Генерация с QA-повтором
    max_attempts = 3
    for attempt in range(max_attempts):
        md_raw = llm.call_llm(prompt)

        qa_result = posts.qa_check_proxy(md_raw)
        if qa_result["ok"]:
            slug_source = f"{topic} {keyword}".strip() if keyword else topic
            slug = posts.make_slug(slug_source)

            now = datetime.now(timezone.utc)
            out_path = CONTENT_DIR / f"{now.year}/{now.month:02d}/{slug}.md"
            out_path.parent.mkdir(parents=True, exist_ok=True)

            title = (topic or "Travel article").strip()
            title_escaped = title.replace('"', '\\"')

            default_category = cfg.get("default_category", "news")
            categories_json = f"['{default_category}']"

            # 🔧 НОВАЯ ЛОГИКА ТЕГОВ + SEO KEYWORDS (РАЗДЕЛЕНИЕ РОЛЕЙ)
            # 1) якорный SEO-ключ (из keywords.json)
            keyword_tag = _norm_tag(keyword)

            # 2) один ключ из СТАТЬИ (приоритетно) или из TOPIC (фоллбэк)
            secondary_tag = _extract_secondary_from_article(md_raw) or _extract_secondary_from_topic(topic)

            # 3) стабильные “клеящие” теги для Related Posts
            base_tags = ["nail-care", "beauty-wellness"]

            # Финальный список тегов (без дублей), порядок: якорь → вторичный → базовые
            tags_list = []
            for t in [keyword_tag, secondary_tag, *base_tags]:
                if t and (t not in tags_list):
                    tags_list.append(t)
            if not tags_list:
                tags_list = ["nail-care"]

            tags_yaml = ", ".join("'" + t.replace("'", "''") + "'" for t in tags_list)

            # SEO: meta keywords — только 1–2 значения (чистый фокус)
            # Используем исходный человеко-читаемый keyword + вторичный (в формате фразы)
            secondary_phrase = secondary_tag.replace("-", " ").strip()
            meta_keywords_parts = []
            if keyword.strip():
                meta_keywords_parts.append(keyword.strip())
            if secondary_phrase and secondary_phrase not in meta_keywords_parts:
                meta_keywords_parts.append(secondary_phrase)
            meta_keywords = ", ".join(meta_keywords_parts)

            fm = (
                f"---\n"
                f'title: "{title_escaped}"\n'
                f"date: {now.isoformat()}\n"  # ✅ убран лишний 'Z'
                f"draft: false\n"
                f"categories: {categories_json}\n"
                f"tags: [{tags_yaml}]\n"
                f'keywords: "{meta_keywords}"\n'
                f'author: "Nailak Editorial"\n'
                f"---\n\n"
            )

            print("🧾 Front-matter preview:")
            print(fm)
            print("───────────────────────────────")

            with open(out_path, "w", encoding="utf-8") as f:
                f.write(fm + md_raw)

            print(f"✓ New post: {out_path}")

            if keywords:
                next_idx = (idx + 1) % len(keywords)
                state["keyword_index"] = next_idx
                save_state(state)

            return
        else:
            print(f"⚠️ Attempt {attempt + 1} failed QA: {qa_result['errors']}")

    # 5️⃣ Если не удалось — черновик
    if cfg.get("draft_if_fail", True):
        now = datetime.now(timezone.utc)
        fallback_slug = posts.make_slug(f"{topic}-draft")
        out_path = CONTENT_DIR / f"{now.year}/{now.month:02d}/{fallback_slug}.md"
        out_path.parent.mkdir(parents=True, exist_ok=True)

        title = (topic or "Travel article").strip()
        title_escaped = title.replace('"', '\\"')
        default_category = cfg.get("default_category", "news")
        categories_json = f"['{default_category}']"

        fm = (
            f"---\n"
            f'title: "{title_escaped}"\n'
            f"date: {now.isoformat()}\n"  # ✅ убран лишний 'Z'
            f"draft: true\n"
            f"categories: {categories_json}\n"
            f"tags: ['draft']\n"
            f'author: "Nailak Editorial"\n'
            f"---\n\n"
            f"(Auto-saved draft after QA failures)\n\n"
        )

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(fm)

        print(f"📝 Saved draft: {out_path}")
    else:
        print("❌ Failed to generate a valid post after retries.")


if __name__ == "__main__":
    main()
