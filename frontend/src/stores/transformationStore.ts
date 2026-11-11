import { create } from 'zustand';
import type { Transformation } from '../types/transformation';

interface TransformationState {
  items: Transformation[];
  current: Transformation | null;
  setItems: (items: Transformation[]) => void;
  setCurrent: (item: Transformation | null) => void;
}

export const useTransformationStore = create<TransformationState>((set) => ({
  items: [],
  current: null,
  setItems: (items) => set({ items }),
  setCurrent: (current) => set({ current }),
}));
