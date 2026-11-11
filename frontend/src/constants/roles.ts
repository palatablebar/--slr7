export const ROLES = ['admin', 'analyst', 'viewer'] as const;
export type Role = (typeof ROLES)[number];
export const ROLE_LABELS: Record<Role, string> = {
  admin: '平台管理员',
  analyst: '数据开发',
  viewer: '报表 owner',
};
export const ROLE_LEVEL: Record<Role, number> = { viewer: 0, analyst: 1, admin: 2 };
