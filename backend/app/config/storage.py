"""共享卷：原始 SQL 与解析快照落盘。"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from app.config.settings import settings
from app.constants import log_templates
from app.utils.logger import log

logger = logging.getLogger("datatrace.storage")


def artifact_root() -> Path:
    root = Path(settings.artifact_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def write_json(kind: str, name: str, payload: dict) -> str:
    directory = artifact_root() / kind
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.json"
    data = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    path.write_text(data, encoding="utf-8")
    log(logger, "ARTIFACT_WRITTEN", level=logging.INFO, kind=kind, path=str(path), bytes=len(data.encode()))
    return str(path)


def write_sql(name: str, sql_text: str) -> str:
    directory = artifact_root() / "sql"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.sql"
    path.write_text(sql_text, encoding="utf-8")
    return str(path)


def read_artifact(path: str) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8")
    except Exception:
        return None
