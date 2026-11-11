import { create } from 'zustand';
import type { ImpactAnalysis } from '../types/impact';

interface ImpactState {
  current: ImpactAnalysis | null;
  history: any[];
  running: boolean;
  setCurrent: (analysis: ImpactAnalysis | null) => void;
  setHistory: (history: any[]) => void;
  setRunning: (running: boolean) => void;
}

export const useImpactStore = create<ImpactState>((set) => ({
  current: null,
  history: [],
  running: false,
  setCurrent: (current) => set({ current }),
  setHistory: (history) => set({ history }),
  setRunning: (running) => set({ running }),
}));
