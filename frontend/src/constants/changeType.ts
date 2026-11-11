export const CHANGE_TYPES = ['add_column', 'drop_column', 'rename_column', 'change_type'] as const;
export type ChangeType = (typeof CHANGE_TYPES)[number];
export const CHANGE_TYPE_LABELS: Record<ChangeType, string> = {
  add_column: '新增列',
  drop_column: '删除列',
  rename_column: '重命名列',
  change_type: '修改列类型',
};
