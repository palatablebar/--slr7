import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ErrorPanel } from '../components/common/ErrorPanel';
import { useAuth } from '../hooks/useAuth';

export function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState('admin@datatrace.local');
  const [password, setPassword] = useState('Demo@2026');
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(email.trim(), password);
      navigate('/assets');
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <h1>DataTrace</h1>
        <div className="sub">Column-level Lineage · Impact Analysis</div>
        <form onSubmit={submit} className="stack">
          <div className="field">
            <label htmlFor="email">邮箱</label>
            <input
              id="email"
              className="input"
              type="email"
              autoComplete="username"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="password">密码</label>
            <input
              id="password"
              className="input"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </div>
          <button className="btn btn-primary" type="submit" disabled={loading} style={{ marginTop: 8 }}>
            {loading ? '登录中…' : '登录'}
          </button>
          <ErrorPanel error={error} />
        </form>
        <div className="login-hint">
          演示账号（密码均为 <code>Demo@2026</code>）：
          <br />
          <code>admin@datatrace.local</code> 平台管理员 · <code>analyst@datatrace.local</code> 数据开发 ·{' '}
          <code>viewer@datatrace.local</code> 报表 owner
        </div>
      </div>
    </div>
  );
}
