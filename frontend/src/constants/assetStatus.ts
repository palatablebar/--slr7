export const ASSET_STATUSES = ['active', 'deprecated', 'draft'] as const;
export type AssetStatus = (typeof ASSET_STATUSES)[number];
export const ASSET_STATUS_LABELS: Record<AssetStatus, string> = {
  active: '启用',
  deprecated: '废弃',
  draft: '草稿',
};
