import { ApiError } from '../../utils/request';

interface Props {
  error: unknown;
  hint?: string;
}

export function ErrorPanel({ error, hint }: Props) {
  if (!error) return null;
  const apiError = error instanceof ApiError ? error : null;
  return (
    <div className="notice warn" style={{ marginTop: 10 }}>
      <div>
        <strong>{apiError ? `${apiError.code}` : '请求失败'}</strong>
        <span style={{ marginLeft: 8 }}>{apiError ? apiError.message : String(error)}</span>
      </div>
      {apiError?.entity && (
        <div className="small muted" style={{ marginTop: 4 }}>
          entity={apiError.entity} {apiError.field ? `field=${apiError.field}` : ''}
        </div>
      )}
      {hint && <div className="small muted" style={{ marginTop: 4 }}>{hint}</div>}
    </div>
  );
}
