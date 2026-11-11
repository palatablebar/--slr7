"""等待数据库可连接（本地开发/迁移前使用）。"""
from __future__ import annotations

import sys
import time

from sqlalchemy import text

from app.config.database import engine


def main(max_attempts: int = 60) -> int:
    for attempt in range(1, max_attempts + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print(f"database ready after {attempt} attempt(s)")
            return 0
        except Exception as exc:  # pragma: no cover
            print(f"waiting for database ({attempt}/{max_attempts}): {exc}", file=sys.stderr)
            time.sleep(1.5)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
