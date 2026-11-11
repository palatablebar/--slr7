"""列变更类型枚举。"""
from enum import Enum


class ChangeType(str, Enum):
    add_column = "add_column"
    drop_column = "drop_column"
    rename_column = "rename_column"
    change_type = "change_type"


CHANGE_TYPE_LABELS = {
    ChangeType.add_column: "新增列",
    ChangeType.drop_column: "删除列",
    ChangeType.rename_column: "重命名列",
    ChangeType.change_type: "修改列类型",
}
