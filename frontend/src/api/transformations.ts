import type { DraftSaveResult, Transformation } from '../types/transformation';
import type { ParsePreview } from '../types/parse';
import { http } from '../utils/request';

export const transformationsApi = {
  list: () => http.get<{ items: Transformation[]; total: number }>('/transformations'),
  detail: (id: string) => http.get<Transformation>(`/transformations/${id}`),
  update: (id: string, payload: Record<string, unknown>) =>
    http.patch<DraftSaveResult>(`/transformations/${id}`, payload),
  discardDraft: (id: string) => http.post<Transformation>(`/transformations/${id}/discard-draft`),
  reparse: (id: string) => http.post<Transformation>(`/transformations/${id}/parse`),
  preview: (id: string, sql_text: string) =>
    http.post<ParsePreview>(`/transformations/${id}/preview`, { sql_text }),
  enqueueParse: (id: string) =>
    http.post<{ task_id: string; queue: string }>(`/transformations/${id}/enqueue-parse`),
};
