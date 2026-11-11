"""哈希与截断工具。"""
from __future__ import annotations

import hashlib


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def truncate(text: str | None, limit: int = 512) -> str:
    if not text:
        return ""
    return text if len(text) <= limit else text[: limit - 1] + "…"
