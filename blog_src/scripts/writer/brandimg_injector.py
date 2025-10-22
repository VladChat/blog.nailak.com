# blog_src/scripts/writer/brandimg_injector.py
# ==========================================================
# 🖼  Brand Image Injector (Version 3 — smart section placement)
# ----------------------------------------------------------
# Всегда вставляет брендовые картинки в Markdown:
#   • первую — в конце первой секции (перед Quick Summary / цитатой / первым H2);
#   • вторую — в конце третьей секции (перед четвёртым H2 или концом файла);
# ALT создаётся из заголовка (# ...) или дефолтного шаблона.
# ==========================================================

import re
import json
from pathlib import Path

DATA_FILE = Path("blog_src/data/brand_images.json")
STATE_FILE = Path("blog_src/data/state.json")


# === Вспомогательные функции ===

def _load_brand_images() -> list[str]:
    """Загружает список доступных изображений из data/brand_images.json."""
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        files = data.get("files", [])
        if not isinstance(files, list):
            raise ValueError("brand_images.json: 'files' must be a list")
        allowed_exts = (".webp", ".jpg", ".jpeg", ".svg", ".png")
        return [f for f in files if f.lower().endswith(allowed_exts)]
    except Exception as e:
        print(f"⚠️ Could not load brand_images.json: {e}")
        return []


def _load_state() -> dict:
    """Загружает state.json или создаёт пустой шаблон."""
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    """Сохраняет state.json."""
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ Could not save state.json: {e}")


def _get_next_image() -> str:
    """Возвращает следующий файл по очереди, циклично записывая индекс в state.json."""
    files = _load_brand_images()
    if not files:
        return "nailak-cover-16x9.webp"

    state = _load_state()
    idx = state.get("brandimg_index", 0)

    chosen = files[idx % len(files)]
    state["brandimg_index"] = (idx + 1) % len(files)

    used = state.get("brandimg_used", [])
    used.append(chosen)
    state["brandimg_used"] = used[-20:]

    _save_state(state)
    return chosen


def _derive_alt(markdown_text: str) -> str:
    """Создаёт ALT из заголовка поста или fallback."""
    m = re.search(r"^#\s+(.+)$", markdown_text, re.MULTILINE)
    if m:
        title = m.group(1).strip()
        return f"{title} — Nailak Cuticle & Nail Oil"
    return "Nailak Cuticle & Nail Oil — natural care and hydration"


# === Основная функция ===

def inject_brand_images(markdown_text: str) -> str:
    """
    Вставляет <figure><img> блоки:
      • первую — в конце первой секции (перед Quick Summary / blockquote / первым H2);
      • вторую — в конце третьей секции (перед четвёртым H2 или концом текста).
    """

    if not markdown_text:
        return markdown_text

    alt_text = _derive_alt(markdown_text)
    text_len = len(markdown_text)

    # --- вычисляем позиции H2, чтобы понимать границы секций ---
    h2_matches = list(re.finditer(r"(?m)^##\s", markdown_text))
    insert_positions: list[int] = []

    # === 1️⃣ Первая вставка — конец первой секции ===
    first_anchor = None

    # ищем Quick Summary или blockquote (как основной ориентир)
    qs_or_bq = re.search(
        r"(?mi)"
        r"^(?:>+\s*)?Quick\s+Summary\b.*$"
        r"|<blockquote\b"
        r"|^>\s",
        markdown_text
    )
    if qs_or_bq:
        first_anchor = qs_or_bq.start()
    elif h2_matches:
        # если нет цитат, но есть заголовки — ставим перед первым H2
        first_anchor = h2_matches[0].start()
    else:
        # резерв — после первого пустого ряда
        first_break = markdown_text.find("\n\n")
        first_anchor = first_break if first_break != -1 else 0

    insert_positions.append(first_anchor)

    # === 2️⃣ Вторая вставка — конец третьей секции ===
    second_anchor = None
    if len(h2_matches) >= 3:
        # если есть минимум три H2, вставляем перед четвёртым (началом 4-й секции)
        next_index = 3 if len(h2_matches) > 3 else len(h2_matches) - 1
        second_anchor = h2_matches[next_index].start()
    elif len(h2_matches) > 0:
        # fallback: если меньше трёх секций — ближе к концу
        second_anchor = len(markdown_text)
    elif text_len > 1500:
        # совсем fallback: середина длинного текста
        mid_pos = text_len // 2
        newline_mid = markdown_text.find("\n", mid_pos)
        if newline_mid != -1:
            second_anchor = newline_mid

    if second_anchor is not None:
        insert_positions.append(second_anchor)

    # --- вставка блоков (с защитой от дублей рядом) ---
    for pos in sorted(set(insert_positions), reverse=True):
        chosen_file = _get_next_image()
        snippet = (
            f'\n\n<figure class="brand-image">'
            f'\n  <img src="/images/brand/{chosen_file}" '
            f'alt="{alt_text}" loading="lazy" decoding="async">'
            f'\n</figure>\n\n'
        )

        window = markdown_text[max(0, pos - 64): min(len(markdown_text), pos + 64)]
        if "<figure" in window:
            continue

        markdown_text = markdown_text[:pos] + snippet + markdown_text[pos:]

    return markdown_text
