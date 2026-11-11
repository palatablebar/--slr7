import type { EdgeKind } from '../constants/edgeKind';

export type { EdgeKind };

export interface GraphNode {
  id: string;
  asset_id: string;
  asset_name: string;
  asset_type: string;
  status?: string;
  column?: string | null;
  depth: number;
  layer?: number;
  column_count?: number;
}

export interface GraphEdge {
  id?: string;
  source: string;
  target: string;
  source_name?: string;
  target_name?: string;
  edge_kind: EdgeKind;
  source_column: string;
  target_column: string;
  transformation_id?: string;
  transformation_name?: string;
  expression_text?: string | null;
  in_cycle?: boolean;
  parse_status?: string;
  edge_count?: number;
}

export interface GraphPayload {
  nodes: GraphNode[];
  edges: GraphEdge[];
  cycle_edges: { source: string; target: string; reason: string }[];
  cycles?: any[];
  depth: number;
  direction: string;
  granularity?: string;
  truncated: boolean;
  start_asset?: { id: string; name: string; asset_type: string };
  asset_nodes?: { id: string; name: string; asset_type: string; status: string; column_count: number }[];
}
