import { useCallback } from 'react';
import { authApi } from '../api/auth';
import { useAuthStore } from '../stores/authStore';

export function useAuth() {
  const { user, token, setSession, setUser, logout, isAnalystOrAbove } = useAuthStore();

  const login = useCallback(
    async (email: string, password: string) => {
      const result = await authApi.login(email, password);
      setSession(result.access_token, result.user);
      return result.user;
    },
    [setSession],
  );

  const refreshMe = useCallback(async () => {
    const me = await authApi.me();
    setUser(me);
    return me;
  }, [setUser]);

  return { user, token, login, refreshMe, logout, isAnalystOrAbove };
}
