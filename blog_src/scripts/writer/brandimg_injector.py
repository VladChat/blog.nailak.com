# blog_src/scripts/writer/brandimg_injector.py
import re
import json
import random
from pathlib import Path

DATA_FILE = Path("blog_src/data/brand_images.json")

def _load_brand_images() -> list[str]:
    """Загружает список доступных изображений из data/brand_images.json."""
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        files = data.get("files", [])
        if not isinstance(files, list):
            raise ValueError("brand_images.json: 'files' must be a list")
        return files
    except Exception as e:
        print(f"⚠️ Could not load brand_images.json: {e}")
        return []

def _pick_random_file() -> str:
    """Выбирает случайный файл из списка доступных, с расширением webp/svg/jpg."""
    files = _load_brand_images()
    allowed_exts = {".webp", ".jpg", ".jpeg", ".svg", ".png"}
    valid = [f for f in files if any(f.lower().endswith(ext) for ext in allowed_exts)]
    if not valid:
        return "nailak-cover-16x9.webp"  # запасной вариант
    return random.choice(valid)

def inject_brand_images(markdown_text: str) -> str:
    """
    Вставляет {{< brandimg file="..." >}}:
      • в КОНЕЦ 1-й секции (перед 2-м заголовком ##),
      • в КОНЕЦ 3-й секции (перед 4-м заголовком ##).

    Каждая вставка получает СВОЙ случайный файл.
    """
    if not markdown_text:
        return markdown_text

    # Находим все H2
    h2_iter = list(re.finditer(r'^##\s+.*$', markdown_text, re.MULTILINE))
    insert_positions = []

    def before_line_start(idx: int) -> int:
        prev_nl = markdown_text.rfind('\n', 0, idx)
        return 0 if prev_nl == -1 else prev_nl + 1

    def after_line_end(idx: int) -> int:
        nl = markdown_text.find('\n', idx)
        return len(markdown_text) if nl == -1 else nl + 1

    # --- Точка вставки №1: конец первой секции (перед вторым H2) ---
    if len(h2_iter) >= 2:
        insert_positions.append(before_line_start(h2_iter[1].start()))
    elif len(h2_iter) == 1:
        insert_positions.append(len(markdown_text))

    # --- Точка вставки №2: конец третьей секции (перед четвёртым H2) ---
    if len(h2_iter) >= 4:
        insert_positions.append(before_line_start(h2_iter[3].start()))
    elif len(h2_iter) >= 3:
        insert_positions.append(len(markdown_text))

    # Вставляем начиная с конца, чтобы индексы не смещались
    for pos in sorted(insert_positions, reverse=True):
        chosen_file = _pick_random_file()  # 🆕 отдельный файл для каждой вставки
        snippet = f'\n\n{{{{< brandimg file="{chosen_file}" >}}}}\n\n'

        window = markdown_text[max(0, pos - 64): min(len(markdown_text), pos + 64)]
        if "{{< brandimg" in window:
            continue
        markdown_text = markdown_text[:pos] + snippet + markdown_text[pos:]

    return markdown_text
