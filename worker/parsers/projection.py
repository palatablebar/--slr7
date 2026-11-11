"""worker/parsers/projection.py：复用 backend/app/parsers/projection.py 的同一份解析实现。

后台 FastAPI 与 worker 共享同一个解析引擎（backend/app/parsers/），
这里只做导出，保证“同步解析”和“异步解析”走完全相同的代码路径。
"""
from app.parsers.projection import *  # noqa: F401,F403
