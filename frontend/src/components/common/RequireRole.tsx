import type { ReactNode } from 'react';
import { ROLE_LEVEL, type Role } from '../../constants/roles';
import { useAuthStore } from '../../stores/authStore';

interface Props {
  minRole: Role;
  children: ReactNode;
  fallback?: ReactNode;
}

export function RequireRole({ minRole, children, fallback }: Props) {
  const user = useAuthStore((state) => state.user);
  const level = user ? ROLE_LEVEL[user.role] : -1;
  if (level < ROLE_LEVEL[minRole]) {
    return (
      <div className="notice warn">
        {fallback || `当前角色（${user?.role || '未登录'}）无权操作，需要 ${minRole} 及以上角色。`}
      </div>
    );
  }
  return <>{children}</>;
}
