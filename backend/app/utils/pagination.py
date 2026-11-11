"""分页工具。"""
from __future__ import annotations

from app.constants.limits import PAGE_SIZE_DEFAULT, PAGE_SIZE_MAX


def clamp_page(page: int | None, page_size: int | None) -> tuple[int, int]:
    p = max(1, int(page or 1))
    size = int(page_size or PAGE_SIZE_DEFAULT)
    size = max(1, min(size, PAGE_SIZE_MAX))
    return p, size


def paginate(items: list, page: int, page_size: int) -> dict:
    total = len(items)
    start = (page - 1) * page_size
    return {
        "items": items[start : start + page_size],
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": start + page_size < total,
    }
