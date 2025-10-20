import json
import re
from datetime import datetime, timezone
from pathlib import Path

from . import llm
from . import posts
from .rss_fetch import get_latest_topic  # ✅ теперь возвращает уже свежую, неиспользованную статью
from .config_loader import load_writer_config

# === 📂 Пути и файлы данных ===
DATA_DIR = Path("blog_src/data")
KEYWORDS_FILE = DATA_DIR / "keywords.json"
STATE_FILE = DATA_DIR / "state.json"
CONTENT_DIR = Path("blog_src/content/posts")


# === 📄 Загрузка шаблона промпта ===
def load_prompt_template() -> str:
    """Читает текстовый шаблон для генерации промпта."""
    with open("blog_src/config/prompt_template.txt", "r", encoding="utf-8") as f:
        return f.read()


# === 🔑 Загрузка ключевых слов ===
def load_keywords() -> list:
    """Загружает keywords.json — основную базу тем и SEO ключей."""
    with open(KEYWORDS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# === 💾 Работа с состоянием ===
def load_state() -> dict:
    """Загружает state.json, если нет — создаёт дефолтную структуру."""
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"keyword_index": 0, "seen": []}


def save_state(state: dict) -> None:
    """Сохраняет state.json с безопасным созданием каталога."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


# === 🧩 Формирование промпта ===
def build_prompt(topic: str, summary: str, original_url: str | None = None) -> str:
    """
    Собирает текст промпта для модели.
    Добавляет контекст и ссылку на оригинальный источник, если есть.
    """
    template = load_prompt_template()
    topic_block = topic
    if original_url:
        topic_block += f"\n\nOriginal source: {original_url}"
    if summary:
        topic_block += f"\n\nContext: {summary}"
    else:
        topic_block += "\n\nContext: "
    return template.format(topic=topic_block)


# === 🏷 Нормализация тега ===
def _norm_tag(s: str) -> str:
    """Преобразует строку в безопасный тег (латиница, дефисы, без мусора)."""
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
    while "--" in t:
        t = t.replace("--", "-")
    return t[:40]


# === 🧠 Извлечение вторичного ключа из статьи ===
def _extract_secondary_from_article(md_text: str, all_keywords: list) -> str:
    """Пытается найти вторичный ключ в тексте статьи (по keywords.json)."""
    if not md_text or not all_keywords:
        return ""
    text_low = md_text.lower()
    for kw in all_keywords:
        if kw.lower() in text_low:
            return _norm_tag(kw)
    return ""


# === 🧠 Альтернатива: вторичный ключ из заголовка ===
def _extract_secondary_from_topic(topic: str, all_keywords: list) -> str:
    """Если в тексте ничего не нашли — ищем совпадение в заголовке."""
    if not topic or not all_keywords:
        return ""
    topic_low = topic.lower()
    for kw in all_keywords:
        if kw.lower() in topic_low:
            return _norm_tag(kw)
    return ""


# === 🧹 Очистка фраз для meta keywords ===
def _clean_phrase_for_meta(s: str) -> str:
    """Делает фразу безопасной для meta keywords."""
    if not s:
        return ""
    s = re.sub(r"\s+", " ", str(s).strip())
    s = re.sub(r"^[,;|/]+", "", s)
    s = re.sub(r"[,;|/]+$", "", s)
    return s


# === 🚀 Главная функция ===
def main():
    cfg = load_writer_config()
    state = load_state()

    print("───────────────────────────────")
    print("🚀 Starting Nailak writer")

    # === 1️⃣ Загрузка ключевых слов ===
    try:
        keywords = load_keywords()
        print(f"✅ Loaded {len(keywords)} keywords")
    except Exception as e:
        print(f"⚠️ Could not load keywords.json: {e}")
        keywords = []

    idx = max(0, int(state.get("keyword_index", 0)))
    primary_keyword = keywords[idx] if keywords and idx < len(keywords) else ""
    print(f"🎯 Current primary keyword: {primary_keyword}")
    print("───────────────────────────────")

    # === 2️⃣ Получение новой статьи через улучшенный rss_fetch ===
    print("🧭 Fetching RSS feed...")
    topic, summary, original_url = get_latest_topic()
    topic = topic or "Daily Nailak Update"
    summary = summary or ""
    original_url = original_url or None

    # 🔹 Проверку дубликатов теперь делает rss_fetch.py — здесь не нужно

    # === 3️⃣ Логирование данных ===
    print("📰 Topic received:")
    print(f"Title: {topic}")
    print(f"Summary: {summary[:400]}{'...' if len(summary) > 400 else ''}")
    print(f"Original URL: {original_url if original_url else '(none)'}")
    print("───────────────────────────────")

    # === 4️⃣ Формируем промпт ===
    prompt = build_prompt(topic, summary, original_url)
    print("🧩 Final topic-context sent to GPT:")
    print(prompt[:600] + ("..." if len(prompt) > 600 else ""))
    print("───────────────────────────────")

    # === 5️⃣ Генерация статьи ===
    max_attempts = 3
    for attempt in range(max_attempts):
        print(f"🤖 Generating article (attempt {attempt + 1}/{max_attempts})...")
        md_raw = llm.call_llm(prompt)
        qa_result = posts.qa_check_proxy(md_raw)
        if qa_result["ok"]:
            print("✅ QA passed.")
            break
        print(f"⚠️ QA failed: {qa_result['errors']}")
    else:
        print("❌ All attempts failed — saving draft.")
        _save_draft(topic, cfg)
        return

    # === 6️⃣ Формирование тегов ===
    secondary_tag = _extract_secondary_from_article(md_raw, keywords) or _extract_secondary_from_topic(topic, keywords)
    if not secondary_tag and keywords:
        secondary_tag = _norm_tag(keywords[(idx + 1) % len(keywords)])

    base_tags = []
    for i in range(2, 5):
        if len(keywords) > i:
            base_tags.append(_norm_tag(keywords[(idx + i) % len(keywords)]))

    keyword_tag = _norm_tag(primary_keyword)
    tags_list = []
    for t in [keyword_tag, secondary_tag, *base_tags]:
        if t and t not in tags_list:
            tags_list.append(t)
    if not tags_list:
        tags_list = ["nail-care"]

    tags_yaml = ", ".join("'" + t.replace("'", "''") + "'" for t in tags_list)

    # === 7️⃣ Формирование meta keywords ===
    primary_phrase = _clean_phrase_for_meta(primary_keyword)
    secondary_phrase = _clean_phrase_for_meta(secondary_tag.replace("-", " "))
    meta_keywords_parts = []
    if primary_phrase:
        meta_keywords_parts.append(primary_phrase)
    if secondary_phrase and secondary_phrase.lower() not in {p.lower() for p in meta_keywords_parts}:
        meta_keywords_parts.append(secondary_phrase)
    keywords_yaml_items = "".join([f'  - "{k}"\n' for k in meta_keywords_parts])
    keywords_block = f"keywords:\n{keywords_yaml_items}" if meta_keywords_parts else "keywords: []\n"

    # === 8️⃣ Сохраняем пост ===
    now = datetime.now(timezone.utc)
    slug_source = f"{topic} {primary_keyword}".strip()
    slug = posts.make_slug(slug_source)
    out_path = CONTENT_DIR / f"{now.year}/{now.month:02d}/{slug}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    title_escaped = topic.replace('"', '\\"')

    fm = (
        f"---\n"
        f'title: "{title_escaped}"\n'
        f"date: {now.isoformat()}\n"
        f"draft: false\n"
        f"categories: ['news']\n"
        f"tags: [{tags_yaml}]\n"
        f"{keywords_block}"
        f'author: "Nailak Editorial"\n'
        f"---\n\n"
    )

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(fm + md_raw)

    print("🧾 Front-matter preview:")
    print(fm)
    print(f"✓ New post saved: {out_path}")
    print("───────────────────────────────")

    if keywords:
        state["keyword_index"] = (idx + 1) % len(keywords)
    save_state(state)
    print(f"🗂 Updated state.json — next keyword index: {state['keyword_index']}")


# === 📝 Сохранение черновика при сбое ===
def _save_draft(topic: str, cfg: dict):
    """Сохраняет черновик, если QA не прошёл или GPT не дал результата."""
    now = datetime.now(timezone.utc)
    fallback_slug = re.sub(r"[^a-zA-Z0-9-]+", "-", topic.lower()) + "-draft"
    out_path = CONTENT_DIR / f"{now.year}/{now.month:02d}/{fallback_slug}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    title_escaped = topic.replace('"', '\\"')

    fm = (
        f"---\n"
        f'title: "{title_escaped}"\n'
        f"date: {now.isoformat()}\n"
        f"draft: true\n"
        f"categories: ['news']\n"
        f"tags: ['draft']\n"
        f'author: "Nailak Editorial"\n'
        f"---\n\n"
        f"(Auto-saved draft after QA failures)\n\n"
    )

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(fm)
    print(f"📝 Draft saved: {out_path}")


if __name__ == "__main__":
    main()
