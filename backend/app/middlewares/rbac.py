"""RBAC 依赖：按能力矩阵判定，越权返回 403 + E_FORBIDDEN。"""
from __future__ import annotations

import logging

from fastapi import Depends

from app.constants import log_templates
from app.constants.error_codes import E_FORBIDDEN
from app.middlewares.auth import get_current_user
from app.models.user import User
from app.services import permission_service
from app.utils.errors import AppError
from app.utils.logger import log
from app.constants.roles import Role, role_can

logger = logging.getLogger("datatrace.rbac")


def require_capability(capability: str):
    def _guard(user: User = Depends(get_current_user)) -> User:
        if not role_can(user.role, capability):
            log(
                logger,
                "RBAC_FORBIDDEN",
                level=logging.WARNING,
                user=str(user.id),
                role=user.role,
                capability=capability,
            )
            raise AppError(
                E_FORBIDDEN,
                f"当前角色 {user.role} 无权执行该操作（需要 {capability} 能力）",
                entity="rbac",
                field=capability,
                detail={"required_capability": capability, "role": user.role},
            )
        return user

    return _guard


def require_role(min_role: str):
    order = {"viewer": 0, "analyst": 1, "admin": 2}
    required_level = order.get(min_role, 2)

    def _guard(user: User = Depends(get_current_user)) -> User:
        if order.get(user.role, -1) < required_level:
            log(
                logger,
                "RBAC_FORBIDDEN",
                level=logging.WARNING,
                user=str(user.id),
                role=user.role,
                capability=f"role>={min_role}",
            )
            raise AppError(
                E_FORBIDDEN,
                f"当前角色 {user.role} 无权执行该操作（需要 {min_role} 及以上）",
                entity="rbac",
                field="role",
                detail={"required_role": min_role, "role": user.role},
            )
        return user

    return _guard


def require_analyst() -> User:
    return Depends(require_capability("transformation:write"))


__all__ = ["require_capability", "require_role", "require_analyst", "Role"]
