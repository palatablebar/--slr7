import type { AuditEntry } from '../types/audit';
import { http } from '../utils/request';

export const auditApi = {
  recent: (limit = 10) => http.get<{ items: AuditEntry[]; total: number }>(`/audit/recent?limit=${limit}`),
};
