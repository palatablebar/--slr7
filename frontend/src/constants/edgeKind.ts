export const EDGE_KINDS = ['direct', 'derived', 'aggregate', 'join_key'] as const;
export type EdgeKind = (typeof EDGE_KINDS)[number];
export const EDGE_KIND_LABELS: Record<EdgeKind, string> = {
  direct: '直传',
  derived: '派生',
  aggregate: '聚合',
  join_key: '关联键',
};
