import { NavLink } from 'react-router-dom';
import { ROLE_LABELS } from '../../constants/roles';
import { useAuthStore } from '../../stores/authStore';

const ITEMS = [
  { to: '/assets', glyph: '▤', label: '资产目录' },
  { to: '/transformations', glyph: '⌘', label: '转换解析' },
  { to: '/lineage', glyph: '⤳', label: '血缘图' },
  { to: '/impact', glyph: '◬', label: '影响分析' },
];

export function RailNav() {
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  return (
    <aside className="rail">
      <div className="rail-logo">DT</div>
      {ITEMS.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          className={({ isActive }) => `rail-item ${isActive ? 'active' : ''}`}
        >
          <span className="rail-glyph">{item.glyph}</span>
          <span className="rail-label">{item.label}</span>
        </NavLink>
      ))}
      <div className="rail-spacer" />
      <div className="rail-item" title={`${user?.display_name || ''} · ${ROLE_LABELS[user?.role || 'viewer']}`}>
        <span className="rail-glyph" style={{ color: 'var(--brass)' }}>
          ◈
        </span>
        <span className="rail-label">{user?.display_name?.slice(0, 4) || '未登录'}</span>
      </div>
      <button
        type="button"
        className="rail-item"
        onClick={logout}
        title="退出登录"
        style={{ background: 'transparent', border: 0, borderLeft: '2px solid transparent' }}
      >
        <span className="rail-glyph">⏻</span>
        <span className="rail-label">退出</span>
      </button>
    </aside>
  );
}
