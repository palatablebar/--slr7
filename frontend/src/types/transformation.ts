import type { ParseStatus } from '../constants/parseStatus';

export type { ParseStatus };

export interface LineageEdgeRow {
  id: number;
  source_asset_id: string;
  source_column: string;
  target_asset_id: string;
  target_column: string;
  edge_kind: string;
  expression_text: string | null;
}

export interface Transformation {
  id: string;
  owner_id: string;
  name: string;
  dialect: string;
  sql_text: string;
  input_asset_ids_json: string[];
  output_asset_id: string;
  parse_status: ParseStatus;
  parse_error: string | null;
  report_json: Record<string, any>;
  version: number;
  updated_at: string;
  output_asset_name: string | null;
  owner_display_name: string | null;
  edge_count: number;
  parse_status_label?: string;
  input_assets?: { id: string; name: string; asset_type: string }[];
  edges?: LineageEdgeRow[];
}
