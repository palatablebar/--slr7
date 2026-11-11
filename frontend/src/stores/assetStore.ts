import { create } from 'zustand';
import type { AssetDetail, DataAsset } from '../types/dataAsset';

interface AssetState {
  assets: DataAsset[];
  groups: Record<string, DataAsset[]>;
  current: AssetDetail | null;
  loading: boolean;
  setList: (assets: DataAsset[], groups: Record<string, DataAsset[]>) => void;
  setCurrent: (asset: AssetDetail | null) => void;
  setLoading: (loading: boolean) => void;
}

export const useAssetStore = create<AssetState>((set) => ({
  assets: [],
  groups: {},
  current: null,
  loading: false,
  setList: (assets, groups) => set({ assets, groups }),
  setCurrent: (current) => set({ current }),
  setLoading: (loading) => set({ loading }),
}));
