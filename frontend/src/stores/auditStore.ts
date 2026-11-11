import { create } from 'zustand';
import type { AuditEntry } from '../types/audit';

interface AuditState {
  items: AuditEntry[];
  setItems: (items: AuditEntry[]) => void;
}

export const useAuditStore = create<AuditState>((set) => ({
  items: [],
  setItems: (items) => set({ items }),
}));
