import type { GraphPayload } from '../types/lineageEdge';
import { http } from '../utils/request';

export const lineageApi = {
  graph: (params: {
    asset_id: string;
    direction?: string;
    depth?: number;
    granularity?: string;
    column?: string | null;
  }) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') query.set(key, String(value));
    });
    return http.get<GraphPayload>(`/lineage/graph?${query.toString()}`);
  },
  column: (assetId: string, column: string) =>
    http.get<any>(`/lineage/column?asset_id=${assetId}&column=${encodeURIComponent(column)}`),
};
