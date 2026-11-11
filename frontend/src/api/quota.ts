import type { Quota } from '../types/quota';
import { http } from '../utils/request';

export const quotaApi = {
  me: () => http.get<Quota>('/quota/me'),
};
