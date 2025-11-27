# ============================================
# File: scripts/cards/core/template_manager.py
# Template discovery and rotation per platform
# ============================================

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from .models import PlatformConfig

# Файл, где храним, какой шаблон уже использовали для каждой платформы
TEMPLATE_STATE_PATH = Path(__file__).resolve().parents[3] / "data" / "social_template_state.json"


def _load_state() -> dict:
    """Читает JSON с состоянием ротации шаблонов."""
    if not TEMPLATE_STATE_PATH.exists():
        print(f"[cards][templates] Файл состояния не найден, начинаем с пустого: {TEMPLATE_STATE_PATH}")
        return {}
    try:
        state = json.loads(TEMPLATE_STATE_PATH.read_text(encoding="utf-8"))
        print(f"[cards][templates] Загружено состояние шаблонов: {state}")
        return state
    except Exception as e:
        print(f"[cards][templates][ERROR] Не удалось прочитать {TEMPLATE_STATE_PATH}: {e}")
        return {}


def _save_state(state: dict) -> None:
    """Сохраняет JSON с состоянием ротации шаблонов."""
    TEMPLATE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    TEMPLATE_STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(f"[cards][templates] Сохранено новое состояние шаблонов: {state}")


def _list_template_files(config: PlatformConfig) -> List[Path]:
    """
    Возвращает список файлов-шаблонов для платформы.

    ВАЖНО: берём все самые типичные форматы и игнорируем регистр расширения:
      - .jpg / .jpeg
      - .png
      - .webp
    Это защищает от ситуации, когда файлы экспортированы как .JPG или .PNG,
    а фильтр стоял строго на '*.jpg'.
    """
    template_dir = Path(config.template_dir)
    if not template_dir.exists():
        print(f"[cards][templates][ERROR] Директория шаблонов не найдена: {template_dir}")
        return []

    allowed_ext = {".jpg", ".jpeg", ".png", ".webp"}

    files: List[Path] = []
    for p in template_dir.iterdir():
        if p.is_file() and p.suffix.lower() in allowed_ext:
            files.append(p)

    files = sorted(files, key=lambda p: p.name.lower())
    print(f"[cards][templates] [{config.name}] Найдено {len(files)} шаблон(ов) в {template_dir}")
    for p in files:
        print(f"[cards][templates]   - {p.name}")

    return files


def get_next_template(config: PlatformConfig) -> Path:
    """
    Возвращает следующий шаблон для платформы с учётом сохранённого состояния.

    Логика:
      - читаем текущее состояние (индекс) для config.name;
      - получаем список файлов-шаблонов;
      - берём templates[idx % len(templates)];
      - сохраняем (idx + 1) % len(templates) обратно в JSON.
    """
    platform_name = config.name
    state = _load_state()

    templates = _list_template_files(config)
    if not templates:
        raise RuntimeError(
            f"Не найдены шаблоны для платформы {platform_name} в {config.template_dir}"
        )

    idx = state.get(platform_name, 0)
    template_path = templates[idx % len(templates)]

    print(
        f"[cards][templates] [{platform_name}] "
        f"Используем шаблон #{idx} из {len(templates)} -> {template_path.name}"
    )

    state[platform_name] = (idx + 1) % len(templates)
    _save_state(state)

    return template_path
