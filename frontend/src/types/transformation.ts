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

/** 未上线草稿：解析状态只代表草稿本身，绝不代表已上线版本。 */
export interface TransformationDraft {
  id: string;
  sql_text: string;
  dialect: string;
  input_asset_ids_json: string[];
  output_asset_id: string;
  parse_status: ParseStatus;
  parse_error: string | null;
  error_line: number | null;
  error_column: number | null;
  report_json: Record<string, any>;
  updated_at: string;
  parse_status_label?: string;
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
  has_draft?: boolean;
  draft?: TransformationDraft | null;
  input_assets?: { id: string; name: string; asset_type: string }[];
  edges?: LineageEdgeRow[];
}

/** 保存草稿的响应：promoted=false 表示草稿未通过校验，上线血缘未变。 */
export interface DraftSaveResult {
  promoted: boolean;
  message: string;
  transformation: Transformation;
}
