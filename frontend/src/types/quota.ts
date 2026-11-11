export interface Quota {
  user_id: string;
  max_sql_bytes: number;
  max_concurrent_parses: number;
  parses_used: number;
  remaining: number;
  max_parses: number;
  window_start: string;
}
