# ============================================
# File: scripts/cards/core/registry.py
# Register all social card platforms
# ============================================

from __future__ import annotations

from typing import Dict, List

from .models import Platform
from ..platforms.instagram import INSTAGRAM_PLATFORM
from ..platforms.facebook import FACEBOOK_PLATFORM
from ..platforms.pinterest import PINTEREST_PLATFORM


_PLATFORMS: Dict[str, Platform] = {
    INSTAGRAM_PLATFORM.config.name: INSTAGRAM_PLATFORM,
    FACEBOOK_PLATFORM.config.name: FACEBOOK_PLATFORM,
    PINTEREST_PLATFORM.config.name: PINTEREST_PLATFORM,
}

print(f"[cards][registry] Зарегистрированы платформы: {list(_PLATFORMS.keys())}")


def get_platforms() -> List[Platform]:
    """Возвращает список всех зарегистрированных платформ."""
    return list(_PLATFORMS.values())


def get_platform(name: str) -> Platform:
    """Возвращает платформу по имени или кидает KeyError, если её нет."""
    return _PLATFORMS[name]
