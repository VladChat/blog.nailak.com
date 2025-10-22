# blog_src/scripts/writer/brandimg_injector.py
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
    """Создаёт ALT из заголовка поста."""
    m = re.search(r"^#\s+(.+)$", markdown_text, re.MULTILINE)
    if m:
        title = m.group(1).strip()
        return f"{title} — Nailak Cuticle & Nail Oil"
    return "Nailak Cuticle & Nail Oil — natural care and hydration"


# === Основная функция ===

def inject_brand_images(markdown_text: str) -> str:
    """
    Вставляет финальные <figure><img> блоки:
      • в НАЧАЛО 1-й секции (сразу ПОСЛЕ первого H2),
      • в НАЧАЛО 3-й секции (сразу ПОСЛЕ третьего H2).
    Каждая вставка получает следующий файл из brand_images.json по циклу.
    """
    if not markdown_text:
        return markdown_text

    alt_text = _derive_alt(markdown_text)
    h2_iter = list(re.finditer(r"^##\s+.*$", markdown_text, re.MULTILINE))
    insert_positions = []

    def after_line_end(idx: int) -> int:
        """Возвращает позицию сразу после конца строки с индексом 'idx'."""
        nl = markdown_text.find("\n", idx)
        return len(markdown_text) if nl == -1 else nl + 1

    # --- Первая вставка: начало первой секции (после 1-го H2) ---
    if len(h2_iter) >= 1:
        insert_positions.append(after_line_end(h2_iter[0].end()))
    else:
        # Если H2 нет совсем — вставляем в начало документа
        insert_positions.append(0)

    # --- Вторая вставка: начало третьей секции (после 3-го H2) ---
    if len(h2_iter) >= 3:
        insert_positions.append(after_line_end(h2_iter[2].end()))

    # --- Вставляем блоки (в обратном порядке, чтобы не сбить индексы) ---
    for pos in sorted(insert_positions, reverse=True):
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
