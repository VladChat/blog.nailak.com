import json
import os
from datetime import datetime, timezone
from pathlib import Path
from openai import OpenAI

from .rss_fetch import get_latest_topic
from .config_loader import load_writer_config
from . import posts

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
    template = load_prompt_template()
    topic_block = topic
    if original_url:
        topic_block = f"{topic_block}\n\nOriginal source: {original_url}"
    if summary:
        topic_block = f"{topic_block}\n\nContext: {summary}"
    else:
        topic_block = f"{topic_block}\n\nContext: "
    return template.format(topic=topic_block)


# ✅ встроенный локальный LLM-вызов (GPT-4o)
def call_llm_local(prompt: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    client = OpenAI(api_key=api_key)
    system_prompt = (
        "You are a blog post writer for nailak.com. "
        "Produce only valid Markdown, well structured, SEO friendly, and detailed."
    )

    try:
        print("ℹ️ Local mode: GPT-4o active (Chat API)")
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=7500,
        )
        content = resp.choices[0].message.content.strip()
        usage = getattr(resp, "usage", None)
        in_tok = getattr(usage, "prompt_tokens", None)
        out_tok = getattr(usage, "completion_tokens", None)
        print(f"ℹ️ Used model gpt-4o, input_tokens={in_tok}, output_tokens={out_tok}")
        return content
    except Exception as e:
        raise RuntimeError(f"LLM local call failed: {e}")


def main():
    cfg = load_writer_config()
    topic, summary, original_url = get_latest_topic()
    topic = topic or "Nail care update"
    summary = summary or ""
    original_url = original_url or None

    print("───────────────────────────────")
    print("📰 Extracted from RSS:")
    print(f"Title: {topic}")
    if summary:
        print(f"Summary: {summary[:400]}{'...' if len(summary) > 400 else ''}")
    else:
        print("Summary: (no summary provided)")
    print(f"Original source: {original_url if original_url else '(not detected)'}")
    print("───────────────────────────────")

    keywords = []
    try:
        keywords = load_keywords()
    except Exception as e:
        print(f"⚠️ Could not load keywords.json: {e}")

    state = load_state()
    idx = max(0, int(state.get("keyword_index", 0)))
    if keywords:
        if idx >= len(keywords):
            idx = 0
        keyword = (keywords[idx] or "").strip()
    else:
        keyword = ""

    prompt = build_prompt(topic, summary, original_url)
    md_raw = call_llm_local(prompt)

    slug_source = f"{topic} {keyword}".strip() if keyword else topic
    slug = posts.make_slug(slug_source)

    now = datetime.now(timezone.utc)
    out_path = CONTENT_DIR / f"{now.year}/{now.month:02d}/{slug}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    title = (topic or "Nail Care Post").strip()
    title_escaped = title.replace('"', '\\"')

    default_category = cfg.get("default_category", "news")
    categories_json = f"['{default_category}']"
    tags_yaml = ", ".join("'" + t.replace("'", "''") + "'" for t in [keyword] if keyword)

    fm = (
        f"---\n"
        f'title: "{title_escaped}"\n'
        f"date: {now.isoformat()}\n"
        f"draft: false\n"
        f"categories: {categories_json}\n"
        f"tags: [{tags_yaml}]\n"
        f'author: "uPatch Editorial"\n'
        f"---\n\n"
    )

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(fm + md_raw)

    print(f"✓ Local post saved: {out_path}")


if __name__ == "__main__":
    main()
