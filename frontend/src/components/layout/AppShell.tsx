import type { ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROLE_LABELS } from '../../constants/roles';
import { useAuthStore } from '../../stores/authStore';
import { RailNav } from './RailNav';

interface Props {
  children: ReactNode;
  eyebrow: string;
  title: string;
  actions?: ReactNode;
}

export function AppShell({ children, eyebrow, title, actions }: Props) {
  const user = useAuthStore((state) => state.user);
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);
  return (
    <div className="app-shell">
      <RailNav />
      <main className="main">
        <header className="page-head">
          <div>
            <div className="eyebrow">
              DataTrace · 列级血缘与影响分析 · {user ? `${user.display_name}（${ROLE_LABELS[user.role]}）` : ''}
            </div>
            <h1 className="display-title">{title}</h1>
          </div>
          <div className="row">
            {actions}
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => {
                logout();
                navigate('/login');
              }}
            >
              退出
            </button>
          </div>
        </header>
        {children}
      </main>
    </div>
  );
}
