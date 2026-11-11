import { create } from 'zustand';
import type { Role } from '../constants/roles';
import type { User } from '../types/user';
import { clearSession, getStoredUser, getToken, setStoredUser, setToken } from '../utils/request';

interface AuthState {
  user: User | null;
  token: string | null;
  loading: boolean;
  setSession: (token: string, user: User) => void;
  setUser: (user: User) => void;
  logout: () => void;
  isRole: (role: Role) => boolean;
  isAnalystOrAbove: () => boolean;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: getStoredUser(),
  token: getToken(),
  loading: false,
  setSession: (token, user) => {
    setToken(token);
    setStoredUser(user);
    set({ token, user });
  },
  setUser: (user) => {
    setStoredUser(user);
    set({ user });
  },
  logout: () => {
    clearSession();
    set({ token: null, user: null });
  },
  isRole: (role) => get().user?.role === role,
  isAnalystOrAbove: () => {
    const role = get().user?.role;
    return role === 'analyst' || role === 'admin';
  },
}));
