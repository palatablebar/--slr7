import { useCallback } from 'react';
import { quotaApi } from '../api/quota';
import { useQuotaStore } from '../stores/quotaStore';

export function useQuota() {
  const { quota, setQuota } = useQuotaStore();
  const load = useCallback(async () => {
    try {
      const result = await quotaApi.me();
      setQuota(result);
      return result;
    } catch {
      return null;
    }
  }, [setQuota]);
  return { quota, load };
}
