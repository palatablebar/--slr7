import type { AssetDetail, DataAsset } from '../types/dataAsset';
import { http } from '../utils/request';

export const assetsApi = {
  list: (params: { q?: string; asset_type?: string; status?: string } = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value) query.set(key, String(value));
    });
    return http.get<{ items: DataAsset[]; total: number; groups: Record<string, DataAsset[]> }>(
      `/assets?${query.toString()}`,
    );
  },
  detail: (id: string) => http.get<AssetDetail>(`/assets/${id}`),
  create: (payload: Record<string, unknown>) => http.post<{ id: string }>('/assets', payload),
  update: (id: string, payload: Record<string, unknown>) =>
    http.patch<{ id: string; schema_changes: unknown[] }>(`/assets/${id}`, payload),
};
