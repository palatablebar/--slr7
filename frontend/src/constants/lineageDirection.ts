export const LINEAGE_DIRECTIONS = ['upstream', 'downstream', 'both'] as const;
export type LineageDirection = (typeof LINEAGE_DIRECTIONS)[number];
export const DIRECTION_LABELS: Record<LineageDirection, string> = {
  upstream: '上游',
  downstream: '下游',
  both: '双向',
};
