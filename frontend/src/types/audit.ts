export interface AuditEntry {
  id: string;
  actor_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  payload_json: Record<string, any>;
  ip: string | null;
  result: string;
  created_at: string;
}
