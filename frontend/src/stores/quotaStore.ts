import { create } from 'zustand';
import type { Quota } from '../types/quota';

interface QuotaState {
  quota: Quota | null;
  setQuota: (quota: Quota | null) => void;
}

export const useQuotaStore = create<QuotaState>((set) => ({
  quota: null,
  setQuota: (quota) => set({ quota }),
}));
