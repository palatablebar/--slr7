"""日志工具：所有日志都经集中模板输出。"""
from __future__ import annotations

import logging

from app.constants import log_templates as T


def log(logger: logging.Logger, template_name: str, level: int = logging.INFO, **kwargs) -> str:
    """按模板名格式化并输出一条日志，返回渲染后的文本。"""
    template = getattr(T, template_name, template_name)
    try:
        message = template.format(**kwargs)
    except Exception:
        message = f"{template_name} {kwargs}"
    logger.log(level, message)
    return message


def summarize_sql(sql_text: str) -> dict:
    from app.utils.hashing import sha256_text

    return {"sql_sha256": sha256_text(sql_text), "sql_bytes": len(sql_text.encode("utf-8"))}
