export const ASSET_TYPES = ['table', 'view', 'materialized_view', 'cte_result'] as const;
export type AssetType = (typeof ASSET_TYPES)[number];
export const ASSET_TYPE_LABELS: Record<AssetType, string> = {
  table: '表',
  view: '视图',
  materialized_view: '物化视图',
  cte_result: 'CTE 结果',
};
export const ASSET_TYPE_SHAPES: Record<AssetType, string> = {
  table: 'rect',
  view: 'cut',
  materialized_view: 'double',
  cte_result: 'dashed',
};
