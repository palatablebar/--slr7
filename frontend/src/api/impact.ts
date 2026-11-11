import type { ImpactAnalysis } from '../types/impact';
import { http } from '../utils/request';

export const impactApi = {
  analyze: (payload: {
    target_asset_id: string;
    target_column?: string | null;
    change_type: string;
    force?: boolean;
  }) => http.post<ImpactAnalysis>('/impact/analyze', payload),
  history: () => http.get<{ items: any[]; total: number }>('/impact/history'),
  detail: (id: string) => http.get<ImpactAnalysis>(`/impact/${id}`),
};
