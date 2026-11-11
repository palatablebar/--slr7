"""Redis 连接（解析结果短期缓存 + Celery broker），不可用时降级。"""
from __future__ import annotations

import json
import logging

import redis

from app.config.settings import settings

logger = logging.getLogger("datatrace.redis")

_client: redis.Redis | None = None


def get_redis() -> redis.Redis | None:
    global _client
    if _client is None:
        try:
            _client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
            _client.ping()
        except Exception as exc:  # pragma: no cover
            logger.warning("redis unavailable, cache disabled: %s", exc)
            _client = None
    return _client


def cache_get(key: str):
    client = get_redis()
    if client is None:
        return None
    try:
        raw = client.get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None


def cache_set(key: str, value, ttl: int = 300) -> None:
    client = get_redis()
    if client is None:
        return
    try:
        client.setex(key, ttl, json.dumps(value, ensure_ascii=False, default=str))
    except Exception:
        pass
