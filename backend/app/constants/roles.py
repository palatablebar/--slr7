"""角色与权限矩阵。"""
from enum import Enum


class Role(str, Enum):
    admin = "admin"
    analyst = "analyst"
    viewer = "viewer"


ROLE_LABELS = {
    Role.admin: "平台管理员",
    Role.analyst: "数据开发",
    Role.viewer: "报表 owner",
}

ROLE_LEVEL = {Role.viewer: 0, Role.analyst: 1, Role.admin: 2}

# 角色→能力矩阵
ROLE_MATRIX = {
    Role.viewer: {"asset:read", "lineage:read", "impact:read"},
    Role.analyst: {
        "asset:read",
        "asset:write",
        "transformation:read",
        "transformation:write",
        "parse:run",
        "impact:read",
        "impact:run",
        "lineage:read",
    },
    Role.admin: {"*"},
}


def role_can(role: str, capability: str) -> bool:
    try:
        r = Role(role)
    except ValueError:
        return False
    caps = ROLE_MATRIX.get(r, set())
    return "*" in caps or capability in caps
