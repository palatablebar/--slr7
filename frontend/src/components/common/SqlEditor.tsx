interface Props {
  value: string;
  onChange: (value: string) => void;
  errorLine?: number | null;
  readOnly?: boolean;
  statusLabel?: string;
}

/** 羊皮纸色 SQL 编辑器：行号 + 出错行高亮（CodeMirror 的轻量替代，见 TESTING.md 已知差异）。 */
export function SqlEditor({ value, onChange, errorLine, readOnly, statusLabel }: Props) {
  const lines = value.split('\n');
  return (
    <div className="sql-pane">
      <div className="sql-toolbar">
        <span className="eyebrow">SQL · postgres</span>
        <span className="mono small muted">{lines.length} 行</span>
        <span style={{ flex: 1 }} />
        {statusLabel && <span className="badge brass">{statusLabel}</span>}
      </div>
      <div className="sql-editor">
        <div className="sql-gutter">
          {lines.map((_, index) => (
            <div key={index} className={errorLine === index + 1 ? 'err-line' : ''}>
              {index + 1}
            </div>
          ))}
        </div>
        <textarea
          className="sql-textarea"
          spellCheck={false}
          readOnly={readOnly}
          value={value}
          onChange={(event) => onChange(event.target.value)}
        />
      </div>
    </div>
  );
}
