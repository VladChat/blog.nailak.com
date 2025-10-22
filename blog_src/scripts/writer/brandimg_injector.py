# blog_src/scripts/writer/brandimg_injector.py
import re
import json
import hashlib
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


def _pick_deterministic_file(seed: str) -> str:
    """
    Детерминированно выбирает файл по хэшу seed.
    Один и тот же seed → всегда один и тот же файл.
    """
    files = _load_brand_images()
    allowed_exts = {".webp", ".jpg", ".jpeg", ".svg", ".png"}
    valid = [f for f in files if any(f.lower().endswith(ext) for ext in allowed_exts)]
    if not valid:
        return "nailak-cover-16x9.webp"
    idx = int(hashlib.md5(seed.encode("utf-8")).hexdigest(), 16) % len(valid)
    return valid[idx]


def inject_brand_images(markdown_text: str) -> str:
    """
    Вставляет {{< brandimg file="..." >}}:
      • в КОНЕЦ 1-й секции (перед 2-м заголовком ##),
      • в КОНЕЦ 3-й секции (перед 4-м заголовком ##).

    Каждая вставка получает свой ДЕТЕРМИНИРОВАННЫЙ файл
    (не меняется между сборками).
    """
    if not markdown_text:
        return markdown_text

    # Находим все H2
    h2_iter = list(re.finditer(r"^##\s+.*$", markdown_text, re.MULTILINE))
    insert_positions = []

    def before_line_start(idx: int) -> int:
        prev_nl = markdown_text.rfind("\n", 0, idx)
        return 0 if prev_nl == -1 else prev_nl + 1

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

    # Извлекаем короткий seed на основе заголовка/URL поста
    # (берём первые 80 символов текста как базу)
    base_seed = hashlib.md5(markdown_text[:80].encode("utf-8")).hexdigest()

    # Вставляем начиная с конца, чтобы индексы не смещались
    for i, pos in enumerate(sorted(insert_positions, reverse=True)):
        # для каждой позиции создаём уникальный seed, чтобы картинки отличались
        seed = f"{base_seed}-{i}"
        chosen_file = _pick_deterministic_file(seed)
        snippet = f'\n\n{{{{< brandimg file="{chosen_file}" >}}}}\n\n'

        window = markdown_text[max(0, pos - 64) : min(len(markdown_text), pos + 64)]
        if "{{< brandimg" in window:
            continue
        markdown_text = markdown_text[:pos] + snippet + markdown_text[pos:]

    return markdown_text
