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

    Если следующего заголовка для упора нет — вставляет в конец текста.
    Один и тот же выбранный файл используется для всех вставок в посте.
    """
    if not markdown_text:
        return markdown_text

    # Находим все H2
    h2_iter = list(re.finditer(r'^##\s+.*$', markdown_text, re.MULTILINE))
    insert_positions = []

    def before_line_start(idx: int) -> int:
        """
        Возвращает позицию начала строки, в которой находится символ с индексом idx.
        Используем для вставки ПЕРЕД заголовком (то есть физически в конец предыдущей секции).
        """
        # Найти предыдущий перевод строки. Если не найден — это самое начало (позиция 0).
        prev_nl = markdown_text.rfind('\n', 0, idx)
        return 0 if prev_nl == -1 else prev_nl + 1

    def after_line_end(idx: int) -> int:
        """
        Позиция сразу после конца строки, в которой находится символ с индексом idx.
        (Сохранено для совместимости и возможного будущего использования.)
        """
        nl = markdown_text.find('\n', idx)
        return len(markdown_text) if nl == -1 else nl + 1

    # --- Точка вставки №1: конец первой секции (перед вторым H2) ---
    if len(h2_iter) >= 2:
        # Перед началом второго заголовка
        insert_positions.append(before_line_start(h2_iter[1].start()))
    elif len(h2_iter) == 1:
        # Только одна секция — вставляем в самый конец текста
        insert_positions.append(len(markdown_text))

    # --- Точка вставки №2: конец третьей секции (перед четвёртым H2) ---
    if len(h2_iter) >= 4:
        # Перед началом четвёртого заголовка
        insert_positions.append(before_line_start(h2_iter[3].start()))
    elif len(h2_iter) >= 3:
        # Есть только три секции — вставляем в конец текста
        insert_positions.append(len(markdown_text))

    # Фиксируем конкретный файл для этого поста (один для всех вставок)
    chosen_file = _pick_random_file()
    snippet = f'\n\n{{{{< brandimg file="{chosen_file}" >}}}}\n\n'

    # Вставляем начиная с конца, чтобы индексы не смещались
    for pos in sorted(insert_positions, reverse=True):
        window = markdown_text[max(0, pos - 64): min(len(markdown_text), pos + 64)]
        if "{{< brandimg" in window:
            # Уже есть рядом вставка — пропускаем, чтобы не дублировать
            continue
        markdown_text = markdown_text[:pos] + snippet + markdown_text[pos:]

    return markdown_text
