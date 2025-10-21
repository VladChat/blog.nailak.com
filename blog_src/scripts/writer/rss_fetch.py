# blog_src/scripts/rss_fetch.py
# -*- coding: utf-8 -*-
"""
Получение новой темы из RSS с дедупликацией и подробным логированием.

Ключевые моменты:
- Ротация RSS-источников (state["last_rss"])
- Дедупликация по state["seen"] (с нормализацией URL)
- Просмотр нескольких фидов по очереди, пока не найдём новый пост
- Подробный лог: что загрузили, сколько записей, что пропущено, что выбрано
- Аккуратное обновление state.json (ограничение размера "seen")
"""

import json
import pathlib
import urllib.parse
import feedparser

STATE_PATH = pathlib.Path("blog_src/data/state.json")
RSS_PATH = pathlib.Path("blog_src/data/rss.json")
KEYWORDS_PATH = pathlib.Path("blog_src/data/keywords.json")

# Максимум запоминаемых ссылок (чтобы state.json не разрастался)
SEEN_MAX = 500
# Сколько записей в каждом фиде проверяем максимум
MAX_ENTRIES_PER_FEED = 15
# Сколько фидов подряд пытаемся обойти за один запуск (обычно хватит всех)
MAX_FEEDS_TO_SCAN = 999999  # по сути "все", оставил как явный лимит


# === 📦 Утилиты работы с JSON ===
def load_json(path: pathlib.Path, default):
    """Безопасно загружает JSON или возвращает default (с логом)."""
    try:
        text = path.read_text(encoding="utf-8")
        data = json.loads(text)
        print(f"📥 Loaded JSON: {path} (size={len(text)} chars)")
        return data
    except Exception as e:
        print(f"⚠️ Failed to load JSON at {path}: {e}. Using default.")
        return default


def save_json(path: pathlib.Path, data):
    """Сохраняет JSON с отступами и UTF-8."""
    try:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"💾 Saved JSON: {path}")
    except Exception as e:
        print(f"❌ Failed to save JSON at {path}: {e}")


# === 🔗 Нормализация URL для лучшей дедупликации ===
def normalize_url(url: str) -> str:
    """
    Удаляем UTM/трекинговые параметры и приводим к предсказуемому виду.
    Это сокращает ложные дубликаты.
    """
    if not url:
        return url
    try:
        parsed = urllib.parse.urlsplit(url.strip())
        q = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        # фильтруем типичные трекинговые параметры
        filtered = [(k, v) for (k, v) in q if k.lower() not in {
            "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
            "gclid", "fbclid", "igshid"
        }]
        new_query = urllib.parse.urlencode(filtered, doseq=True)
        normalized = urllib.parse.urlunsplit((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/"),
            new_query,
            ""  # fragment убираем
        ))
        return normalized
    except Exception:
        return url.strip()


# === 🧠 Основная функция получения новой темы ===
def get_latest_topic():
    """
    Загружает RSS-ленты из rss.json и возвращает первую ещё не использованную статью.
    🔹 Пропускает уже встречавшиеся ссылки (state["seen"])
    🔹 Ротирует RSS-источники и keyword-индекс
    🔹 Идёт по фидам по очереди, пока не найдёт новый пост
    Возвращает: (topic_with_keyword, summary, original_url)
    """

    # 1) Загружаем данные
    rss_list = load_json(RSS_PATH, [])
    keywords = load_json(KEYWORDS_PATH, [])
    state = load_json(STATE_PATH, {"last_keyword": -1, "last_rss": -1, "seen": []})

    if not rss_list:
        raise RuntimeError("⚠️ rss.json is empty")
    if not keywords:
        raise RuntimeError("⚠️ keywords.json is empty")

    # 2) Подготовка состояния
    last_rss = int(state.get("last_rss", -1))
    last_keyword = int(state.get("last_keyword", -1))
    seen_raw = state.get("seen", [])
    # нормализуем уже виденные URL
    seen = {normalize_url(u) for u in seen_raw if isinstance(u, str) and u.strip()}

    print("───────────────────────────────")
    print("🚀 RSS Picker starting")
    print(f"📚 RSS sources: {len(rss_list)} | 🧠 seen cache: {len(seen)} | 🔑 keywords: {len(keywords)}")
    print(f"🔁 Start rotation from RSS index: {last_rss + 1} (mod {len(rss_list)})")

    # 3) Перебор фидов с ротацией
    feeds_scanned = 0
    selected = None
    selected_feed_index = None
    selected_feed_url = None

    while feeds_scanned < min(len(rss_list), MAX_FEEDS_TO_SCAN):
        rss_index = (last_rss + 1 + feeds_scanned) % len(rss_list)
        rss_url = rss_list[rss_index]
        feeds_scanned += 1

        print("───────────────────────────────")
        print(f"🌐 Checking RSS feed [{rss_index}]: {rss_url}")

        feed = feedparser.parse(rss_url)

        # Ловим парсерные предупреждения (bozo)
        if getattr(feed, "bozo", 0):
            print(f"⚠️ feedparser bozo=True for {rss_url}: {getattr(feed, 'bozo_exception', None)}")

        entries = getattr(feed, "entries", []) or []
        print(f"📦 Entries found: {len(entries)}")

        if not entries:
            print("⏭️ No entries in this feed. Moving on.")
            continue

        # 4) Перебираем записи в этом фиде
        checked = 0
        skipped = 0
        for entry in entries[:MAX_ENTRIES_PER_FEED]:
            checked += 1
            raw_link = (entry.get("link") or "").strip()
            if not raw_link:
                print("⚪ Entry without link — skip")
                skipped += 1
                continue

            link = normalize_url(raw_link)
            if link in seen:
                print(f"🔁 Seen already: {raw_link}")
                skipped += 1
                continue

            # Нашли новую
            selected = entry
            selected_feed_index = rss_index
            selected_feed_url = rss_url
            print(f"✅ Selected NEW article after checking {checked} entries "
                  f"(skipped {skipped}) in feed [{rss_index}]")
            break

        if selected:
            break

        print(f"⏭️ No new articles in feed [{rss_index}] (checked {checked}, skipped {skipped}). Next feed...")

    # 5) Если ничего не нашли во всех фидах — аккуратный fallback
    if not selected:
        # Возьмём самую свежую запись из первого фида по ротации, но явно залогируем это.
        fallback_index = (last_rss + 1) % len(rss_list)
        fallback_url = rss_list[fallback_index]
        feed = feedparser.parse(fallback_url)
        entries = getattr(feed, "entries", []) or []

        print("───────────────────────────────")
        print("⚠️ No NEW articles across all feeds (all seen).")
        if not entries:
            raise RuntimeError("❌ No entries available in fallback feed either — nothing to publish.")
        selected = entries[0]
        selected_feed_index = fallback_index
        selected_feed_url = fallback_url
        print(f"♻️ Reusing MOST RECENT article from feed [{fallback_index}]: {selected.get('link','')}")
        # Важно: в этом fallback не добавляем ссылку в seen, чтобы не «захламлять» историю при вынужденном повторе.

    # 6) Формируем результат
    topic = (selected.get("title") or "Untitled").strip()
    summary = (selected.get("summary") or "").strip()
    orig_link = (selected.get("link") or "").strip()

    # 7) Ротация ключевых слов
    keyword_index = (last_keyword + 1) % len(keywords)
    keyword = keywords[keyword_index]

    # 8) Обновляем состояние и сохраняем
    state["last_rss"] = selected_feed_index
    state["last_keyword"] = keyword_index

    # Линку добавляем в seen только если это действительно новая (не fallback-повтор)
    if orig_link and normalize_url(orig_link) not in seen:
        state_seen = state.get("seen", [])
        state_seen.append(orig_link)
        # ограничиваем длину
        if len(state_seen) > SEEN_MAX:
            state_seen = state_seen[-SEEN_MAX:]
        state["seen"] = state_seen

    save_json(STATE_PATH, state)

    # 9) Итоговый лог — красиво и подробно
    print("───────────────────────────────")
    print(f"📰 RSS Source: {selected_feed_url}")
    print(f"🧩 Topic: {topic}")
    print(f"📄 Summary: {summary[:250]}{'...' if len(summary) > 250 else ''}")
    print(f"🔗 Link: {orig_link}")
    print(f"🎯 Using keyword: {keyword} (index {keyword_index})")
    print(f"🔄 last_rss -> {state['last_rss']} | 🔑 last_keyword -> {state['last_keyword']}")
    print(f"🗂 seen size -> {len(state.get('seen', []))}")
    print("───────────────────────────────")

    # 10) Возврат в main.py
    return f"{topic} — {keyword}", summary, orig_link
