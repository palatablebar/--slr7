import type { AssetStatus, AssetType } from '../constants/assetType';

export type { AssetStatus, AssetType };

export interface AssetColumn {
  name: string;
  data_type: string | null;
  nullable: boolean | null;
  ordinal?: number | null;
  description?: string | null;
  upstream_count?: number;
  downstream_count?: number;
}

export interface DataAsset {
  id: string;
  owner_id: string;
  name: string;
  asset_type: AssetType;
  database_name: string;
  schema_name: string;
  description: string | null;
  status: AssetStatus;
  updated_at: string;
  column_count: number;
  display_name: string;
  full_name: string;
  asset_type_label?: string;
}

export interface OneHopEdge {
  edge_id?: number;
  asset_id: string;
  asset_name: string;
  asset_type: AssetType;
  source_column: string;
  target_column: string;
  edge_kind: string;
  expression_text: string | null;
  transformation_id: string;
}

export interface AssetDetail extends DataAsset {
  columns: AssetColumn[];
  owner_display_name: string | null;
  upstream_assets: OneHopEdge[];
  downstream_assets: OneHopEdge[];
  producer_transformations: { id: string; name: string; parse_status: string; version: number }[];
  consumer_transformations: { id: string; name: string; parse_status: string; version: number }[];
  schema_changes: {
    id: number;
    change_type: string;
    column_name: string;
    old_type: string | null;
    new_type: string | null;
    source: string;
    detected_at: string;
  }[];
  recent_audits: { id: string; action: string; result: string; created_at: string }[];
}
