import json
import re
from .brandimg_injector import inject_brand_images  # NEW

from datetime import datetime, timezone
from pathlib import Path

from . import llm
from . import posts
from .rss_fetch import get_latest_topic  # ✅ выбирает свежую статью и вращает keyword-индекс
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


# === 💾 Работа с состоянием (оставляем для совместимости, хотя state ведёт rss_fetch) ===
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
def build_prompt(primary_keyword: str, rss_summary: str, original_url: str | None = None) -> str:
    """
    Собирает текст промпта для модели.

    ВАЖНО:
    - Основная тема статьи задаётся ТОЛЬКО primary_keyword.
    - RSS-источник используется только для одного референс-абзаца
      в середине статьи (2–3 предложения) и не влияет на заголовок
      или структуру.
    """
    template = load_prompt_template()

    blocks: list[str] = []
    pk = (primary_keyword or "").strip()
    blocks.append(f"Main keyword: {pk if pk else '(none)'}")

    if original_url:
        blocks.append("")
        blocks.append(
            "External reference (for ONE short 2–3 sentence supporting paragraph "
            "in the middle of the article; keep it loosely connected to the keyword "
            "and end that paragraph with `(source: URL)`):"
        )
        blocks.append(f"URL: {original_url}")

    if rss_summary:
        blocks.append("")
        blocks.append("Source summary (optional):")
        blocks.append(rss_summary)

    topic_block = "\n".join(blocks)
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


# === 🔍 Извлечение H1 заголовка из markdown ===
def _extract_h1_title(md_text: str) -> str:
    """Возвращает текст первого H1 (# ...) из markdown-статьи."""
    if not md_text:
        return ""
    for line in md_text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return ""


# === 🚀 Главная функция ===
def main():
    cfg = load_writer_config()

    print("───────────────────────────────")
    print("🚀 Starting Nailak writer")

    # === 1️⃣ Загрузка ключевых слов ===
    try:
        keywords = load_keywords()
        print(f"✅ Loaded {len(keywords)} keywords")
    except Exception as e:
        print(f"⚠️ Could not load keywords.json: {e}")
        keywords = []

    # === 2️⃣ Получение RSS-источника и keyword через rss_fetch ===
    print("🧭 Fetching RSS feed...")
    topic_raw, summary, original_url = get_latest_topic()
    topic_raw = topic_raw or "Daily Nailak Update"
    summary = summary or ""
    original_url = original_url or None

    # topic_raw ожидается в формате: "<rss_title> — <keyword>"
    primary_keyword = ""
    rss_title_for_log = topic_raw
    if "—" in topic_raw:
        left, right = topic_raw.rsplit("—", 1)
        rss_title_for_log = (left or "").strip() or "Untitled source"
        primary_keyword = (right or "").strip()
    else:
        primary_keyword = topic_raw.strip()

    # Fallback, если по какой-то причине keyword не получился
    if not primary_keyword and keywords:
        primary_keyword = str(keywords[0]).strip()

    # Пытаемся найти индекс этого keyword в списке для ротации base-тегов
    idx = 0
    if keywords and primary_keyword:
        try:
            idx = max(0, int(keywords.index(primary_keyword)))
        except ValueError:
            idx = 0

    print(f"🎯 Primary keyword (from rotation): {primary_keyword}")
    print("📰 RSS reference received:")
    print(f"Source title: {rss_title_for_log}")
    print(f"Summary: {summary[:400]}{'...' if len(summary) > 400 else ''}")
    print(f"Original URL: {original_url if original_url else '(none)'}")
    print("───────────────────────────────")

    # === 3️⃣ Формируем промпт ===
    prompt = build_prompt(primary_keyword, summary, original_url)
    print("🧩 Final prompt context sent to GPT:")
    print(prompt[:600] + ("..." if len(prompt) > 600 else ""))
    print("───────────────────────────────")

    # === 4️⃣ Генерация статьи ===
    max_attempts = 3
    generated_title = ""
    md_raw = ""
    for attempt in range(max_attempts):
        print(f"🤖 Generating article (attempt {attempt + 1}/{max_attempts})...")
        md_raw = llm.call_llm(prompt)
        qa_result = posts.qa_check_proxy(md_raw)
        if qa_result["ok"]:
            print("✅ QA passed.")
            generated_title = _extract_h1_title(md_raw)
            # ✅ Автовставка брендовых картинок в середину текста (после 1-й и 3-й секции)
            md_raw = inject_brand_images(md_raw)
            break
        print(f"⚠️ QA failed: {qa_result['errors']}")
    else:
        print("❌ All attempts failed — saving draft.")
        # Для черновика используем keyword как более устойчивую «тему»
        _save_draft(primary_keyword or topic_raw, cfg)
        return

    # === 5️⃣ Формирование тегов ===
    secondary_tag = (
        _extract_secondary_from_article(md_raw, keywords)
        or _extract_secondary_from_topic(generated_title or primary_keyword, keywords)
    )
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

    # === 6️⃣ Формирование meta keywords ===
    primary_phrase = _clean_phrase_for_meta(primary_keyword)
    secondary_phrase = _clean_phrase_for_meta(secondary_tag.replace("-", " ")) if secondary_tag else ""
    meta_keywords_parts = []
    if primary_phrase:
        meta_keywords_parts.append(primary_phrase)
    if secondary_phrase and secondary_phrase.lower() not in {p.lower() for p in meta_keywords_parts}:
        meta_keywords_parts.append(secondary_phrase)
    keywords_yaml_items = "".join([f'  - "{k}"\n' for k in meta_keywords_parts])
    keywords_block = f"keywords:\n{keywords_yaml_items}" if meta_keywords_parts else "keywords: []\n"

    # === 7️⃣ Сохраняем пост ===
    now = datetime.now(timezone.utc)

    # slug формируем по сгенерированному заголовку; если его нет — по keyword
    slug_source = generated_title or primary_keyword or topic_raw
    slug = posts.make_slug(slug_source)
    out_path = CONTENT_DIR / f"{now.year}/{now.month:02d}/{slug}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    title_for_frontmatter = generated_title or primary_keyword or rss_title_for_log or "Daily Nailak Update"
    title_escaped = title_for_frontmatter.replace('"', '\\"')

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
    # NOTE: rss_fetch now advances and saves keyword index.
    # (Manual bump in this file отсутствует, чтобы не было двойного сдвига и рассинхронизации)


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
