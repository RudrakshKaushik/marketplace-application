"""
Cache helpers that never crash requests when Redis is unavailable or at capacity.
"""

from __future__ import annotations

import logging
from typing import Any

from django.core.cache import cache

logger = logging.getLogger(__name__)


def cache_get(key: str, default: Any = None) -> Any:
    try:
        return cache.get(key, default)
    except Exception as exc:
        logger.warning("Cache get failed for %s: %s", key, exc)
        return default


def cache_set(key: str, value: Any, timeout: int | None = None) -> bool:
    try:
        cache.set(key, value, timeout)
        return True
    except Exception as exc:
        logger.warning("Cache set failed for %s: %s", key, exc)
        return False


def cache_delete(key: str) -> None:
    try:
        cache.delete(key)
    except Exception as exc:
        logger.warning("Cache delete failed for %s: %s", key, exc)


def cache_delete_many(keys: list[str]) -> None:
    if not keys:
        return
    try:
        cache.delete_many(keys)
    except Exception as exc:
        logger.warning("Cache delete_many failed: %s", exc)


def cache_get_or_set(key: str, default_factory, timeout: int | None = None) -> Any:
    cached = cache_get(key)
    if cached is not None:
        return cached

    value = default_factory() if callable(default_factory) else default_factory
    cache_set(key, value, timeout)
    return value
