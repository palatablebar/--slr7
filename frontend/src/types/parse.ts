export interface ParsePreview {
  parse_status: string;
  parse_error: string | null;
  error_line: number | null;
  error_column: number | null;
  warnings: string[];
  unresolved: { reason: string; column?: string; missing?: string[]; detail?: string }[];
  columns: { target_column: string; sources: { asset_id: string; column: string; edge_kind: string }[] }[];
  report: { edge_count: number; star_expanded?: boolean };
}
