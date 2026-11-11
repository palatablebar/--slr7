"""权限判定（RBAC）。"""
from __future__ import annotations

from app.constants.error_codes import E_FORBIDDEN
from app.constants.roles import Role, role_can
from app.utils.errors import AppError


def ensure(role: str, capability: str) -> None:
    if not role_can(role, capability):
        raise AppError(E_FORBIDDEN, entity="permission", detail={"capability": capability, "role": role})


def is_admin(role: str) -> bool:
    return role == Role.admin.value


def is_analyst_or_above(role: str) -> bool:
    return role in (Role.analyst.value, Role.admin.value)


def ensure_owner_or_admin(role: str, user_id, owner_id) -> None:
    if is_admin(role):
        return
    if str(user_id) != str(owner_id):
        raise AppError(E_FORBIDDEN, entity="ownership", detail={"reason": "只允许修改自己创建的记录"})
