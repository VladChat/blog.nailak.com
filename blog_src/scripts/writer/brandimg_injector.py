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
    Ставит {{< brandimg file="..." >}} после 1-й и 3-й секции (заголовков "## ...").
    Файл выбирается случайно один раз на момент генерации и фиксируется в тексте.
    """
    if not markdown_text:
        return markdown_text

    h2_iter = list(re.finditer(r'^##\s+.*$', markdown_text, re.MULTILINE))
    insert_positions = []

    def after_line_end(idx: int) -> int:
        nl = markdown_text.find('\n', idx)
        return len(markdown_text) if nl == -1 else nl + 1

    if len(h2_iter) >= 1:
        insert_positions.append(after_line_end(h2_iter[0].end()))
    if len(h2_iter) >= 3:
        insert_positions.append(after_line_end(h2_iter[2].end()))

    # Фиксируем конкретный файл для этого поста
    chosen_file = _pick_random_file()
    snippet = f'\n\n{{{{< brandimg file="{chosen_file}" >}}}}\n\n'

    for pos in sorted(insert_positions, reverse=True):
        window = markdown_text[max(0, pos - 64): min(len(markdown_text), pos + 64)]
        if "{{< brandimg" in window:
            continue
        markdown_text = markdown_text[:pos] + snippet + markdown_text[pos:]

    return markdown_text
