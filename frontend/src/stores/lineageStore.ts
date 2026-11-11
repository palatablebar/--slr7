import { create } from 'zustand';
import type { LineageDirection } from '../constants/lineageDirection';
import type { GraphPayload, GraphNode } from '../types/lineageEdge';

interface LineageState {
  graph: GraphPayload | null;
  direction: LineageDirection;
  depth: number;
  granularity: 'asset' | 'column';
  selectedNode: GraphNode | null;
  setGraph: (graph: GraphPayload | null) => void;
  setDirection: (direction: LineageDirection) => void;
  setDepth: (depth: number) => void;
  setGranularity: (granularity: 'asset' | 'column') => void;
  setSelectedNode: (node: GraphNode | null) => void;
}

export const useLineageStore = create<LineageState>((set) => ({
  graph: null,
  direction: 'both',
  depth: 3,
  granularity: 'asset',
  selectedNode: null,
  setGraph: (graph) => set({ graph }),
  setDirection: (direction) => set({ direction }),
  setDepth: (depth) => set({ depth }),
  setGranularity: (granularity) => set({ granularity }),
  setSelectedNode: (selectedNode) => set({ selectedNode }),
}));
