import { SAMPLE_SQL } from '../../constants/messages';

interface Props {
  title: string;
  hint: string;
  actionLabel?: string;
  onAction?: () => void;
  sampleSql?: string;
}

export function EmptyState({ title, hint, actionLabel, onAction, sampleSql }: Props) {
  return (
    <div className="empty-state">
      <div className="panel-title" style={{ marginBottom: 8 }}>
        {title}
      </div>
      <div className="small">{hint}</div>
      {actionLabel && onAction && (
        <button type="button" className="btn" style={{ marginTop: 14 }} onClick={onAction}>
          {actionLabel}
        </button>
      )}
      {sampleSql && <pre className="sample-sql">{sampleSql || SAMPLE_SQL}</pre>}
    </div>
  );
}
