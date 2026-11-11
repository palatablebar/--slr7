import type { ImpactSeverity } from '../constants/impactSeverity';

export type { ImpactSeverity };

export interface ImpactNode {
  asset_id: string;
  asset_name: string;
  asset_type: string;
  column: string;
  depth: number;
  edge_kind: string;
  severity: string;
}

export interface ImpactReport {
  target: { asset_id: string; asset_name: string; column: string | null; change_type: string };
  summary: {
    severity: string;
    severity_label: string;
    affected_assets: number;
    affected_columns: number;
    reports: number;
    min_depth: number | null;
    max_depth: number;
    truncated: boolean;
    depth_limit: number;
  };
  nodes: ImpactNode[];
  paths: { target: { asset_id: string; asset_name: string; column: string }; depth: number; path: any[] }[];
  cycles: { nodes: any[]; sample_path: any[] }[];
  cycle_hit: boolean;
  migration_checklist: {
    asset_id: string;
    asset_name: string;
    column: string;
    action: string;
    suggested_sql: string;
    reason: string;
    severity: string;
    depth: number;
  }[];
  truncated: boolean;
  excluded_from_checklist: string[];
}

export interface ImpactAnalysis {
  id: string;
  requested_by: string;
  change_type: string;
  target_asset_id: string;
  target_column: string | null;
  severity: ImpactSeverity;
  affected_count: number;
  report_json: ImpactReport;
  created_at: string;
  cached: boolean;
  target_asset_name: string | null;
}
