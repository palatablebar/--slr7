import { EDGE_KIND_LABELS, type EdgeKind } from '../../constants/edgeKind';
import { findColumnSnippet } from '../../utils/sqlSnippet';
import { ColumnTag } from '../common/ColumnTag';

interface Props {
  title?: string;
  column?: string | null;
  sqlText?: string;
  edges?: {
    edge_kind: string;
    source_column: string;
    target_column: string;
    expression_text?: string | null;
    transformation_name?: string;
    direction: string;
  }[];
  onColumnSelect?: (column: string) => void;
}

/** 右侧 340px 资产检查器（可折叠，切换内容时 160ms 位移淡入）。 */
export function AssetInspector({ title, column, sqlText, edges = [], onColumnSelect }: Props) {
  return (
    <aside className="inspector">
      <div className="inspector-enter" key={`${title}-${column}`}>
        <div className="eyebrow">资产检查器</div>
        <div className="panel-title" style={{ marginTop: 4 }}>
          {title || '选择图上的节点'}
        </div>
        {column && (
          <div style={{ marginTop: 10 }}>
            <ColumnTag column={column} dark />
          </div>
        )}
        {column && sqlText && (
          <div className="inspector-section">
            <div className="eyebrow">上游表达式片段</div>
            <pre className="mono small" style={{ whiteSpace: 'pre-wrap', color: 'var(--parch)', marginTop: 6 }}>
              {findColumnSnippet(sqlText, column).snippet || '（该列没有可定位的表达式片段）'}
            </pre>
          </div>
        )}
        <div className="inspector-section">
          <div className="eyebrow">列级边（{edges.length}）</div>
          <div className="stack" style={{ marginTop: 8 }}>
            {edges.length === 0 && <div className="small muted">没有匹配的列级边。</div>}
            {edges.map((edge, index) => (
              <div key={index} className="panel" style={{ padding: '8px 10px' }}>
                <div className="row small" style={{ justifyContent: 'space-between' }}>
                  <span className="mono">
                    {edge.source_column} → {edge.target_column}
                  </span>
                  <span className="badge brass">
                    {EDGE_KIND_LABELS[edge.edge_kind as EdgeKind] || edge.edge_kind}
                  </span>
                </div>
                <div className="small muted" style={{ marginTop: 4 }}>
                  {edge.transformation_name || '转换'} · {edge.direction}
                </div>
                {edge.expression_text && (
                  <div className="mono small" style={{ marginTop: 4, color: 'var(--brass)' }}>
                    {edge.expression_text.length > 120
                      ? `${edge.expression_text.slice(0, 119)}…`
                      : edge.expression_text}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </aside>
  );
}
