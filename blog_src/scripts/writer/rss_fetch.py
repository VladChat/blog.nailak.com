import json
import pathlib
import feedparser

STATE_PATH = pathlib.Path("blog_src/data/state.json")
RSS_PATH = pathlib.Path("blog_src/data/rss.json")
KEYWORDS_PATH = pathlib.Path("blog_src/data/keywords.json")


# === 📂 Вспомогательные функции ===
def load_json(path, default):
    """Безопасно загружает JSON или возвращает default."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path, data):
    """Сохраняет JSON с отступами и UTF-8."""
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# === 🧠 Основная функция получения новой темы ===
def get_latest_topic():
    """
    Загружает RSS-ленты из rss.json и возвращает первую ещё не использованную статью.
    🔹 Пропускает уже встречавшиеся ссылки (из state["seen"])
    🔹 Ведёт ротацию RSS-источников и keyword-индекса
    🔹 Возвращает: (topic, summary, original_url)
    """
    rss_list = load_json(RSS_PATH, [])
    keywords = load_json(KEYWORDS_PATH, [])
    state = load_json(STATE_PATH, {"last_keyword": -1, "last_rss": -1, "seen": []})

    if not rss_list:
        raise RuntimeError("⚠️ rss.json is empty")
    if not keywords:
        raise RuntimeError("⚠️ keywords.json is empty")

    # === 1️⃣ RSS rotation ===
    rss_index = (state.get("last_rss", -1) + 1) % len(rss_list)
    rss_url = rss_list[rss_index]
    print(f"🌐 Checking RSS feed: {rss_url}")
    feed = feedparser.parse(rss_url)

    if not feed.entries:
        raise RuntimeError(f"⚠️ No entries found in RSS: {rss_url}")

    seen = set(state.get("seen", []))
    selected_entry = None

    # === 2️⃣ Перебираем статьи, ищем первую новую ===
    for entry in feed.entries[:10]:  # анализируем до 10 свежих постов
        link = entry.get("link", "")
        if not link:
            continue
        if link in seen:
            print(f"🔁 Skipped already used: {link}")
            continue
        selected_entry = entry
        print(f"✅ Selected new article: {link}")
        break

    # === 3️⃣ Если ничего нового не нашли — fallback ===
    if not selected_entry:
        latest_entry = feed.entries[0]
        print("⚠️ All recent articles were already processed. Reusing the most recent.")
        selected_entry = latest_entry

    topic = selected_entry.get("title", "Untitled").strip()
    summary = selected_entry.get("summary", "").strip()
    link = selected_entry.get("link", "").strip()

    # === 4️⃣ Keyword rotation ===
    keyword_index = (state.get("last_keyword", -1) + 1) % len(keywords)
    keyword = keywords[keyword_index]

    # === 5️⃣ Сохраняем обновлённое состояние ===
    state["last_rss"] = rss_index
    state["last_keyword"] = keyword_index
    if link:
        seen_list = state.get("seen", [])
        seen_list.append(link)
        state["seen"] = seen_list[-100:]  # храним только последние 100 ссылок
    save_json(STATE_PATH, state)

    # === 6️⃣ Логирование итогов ===
    print("───────────────────────────────")
    print(f"📰 RSS Source: {rss_url}")
    print(f"🧩 Topic: {topic}")
    print(f"📄 Summary: {summary[:250]}{'...' if len(summary) > 250 else ''}")
    print(f"🔗 Link: {link}")
    print(f"🎯 Using keyword: {keyword} (index {keyword_index})")
    print("───────────────────────────────")

    # === 7️⃣ Возврат данных в main.py ===
    return f"{topic} — {keyword}", summary, link
