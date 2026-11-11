import { EDGE_KIND_LABELS, type EdgeKind } from '../../constants/edgeKind';
import { SEVERITY_LABELS, SEVERITY_ORDER, type ImpactSeverity } from '../../constants/impactSeverity';
import type { ImpactNode } from '../../types/impact';
import { ColumnTag } from './ColumnTag';

interface Props {
  nodes: ImpactNode[];
}

/** 受影响资产与列：多段表头 + 按严重度排序/分组。 */
export function ImpactTable({ nodes }: Props) {
  const sorted = [...nodes].sort((a, b) => {
    const severityDiff =
      (SEVERITY_ORDER[b.severity as ImpactSeverity] ?? 0) - (SEVERITY_ORDER[a.severity as ImpactSeverity] ?? 0);
    return severityDiff !== 0 ? severityDiff : a.depth - b.depth;
  });
  return (
    <table className="data-table dark">
      <thead>
        <tr>
          <th>严重度</th>
          <th>资产</th>
          <th>列</th>
          <th>传播深度</th>
          <th>边类型</th>
          <th>建议动作</th>
        </tr>
      </thead>
      <tbody>
        {sorted.map((node) => (
          <tr key={`${node.asset_id}-${node.column}`}>
            <td>
              <span className={`sev ${node.severity}`} style={{ fontSize: '0.95rem' }}>
                {SEVERITY_LABELS[node.severity as ImpactSeverity] || node.severity}
              </span>
            </td>
            <td className="mono">{node.asset_name}</td>
            <td>
              <ColumnTag column={node.column} />
            </td>
            <td className="mono">{node.depth}</td>
            <td>{EDGE_KIND_LABELS[node.edge_kind as EdgeKind] || node.edge_kind}</td>
            <td className="small muted">
              {node.edge_kind === 'aggregate' || node.edge_kind === 'derived'
                ? 'add_cast / rewrite_sql'
                : 'rewrite_sql'}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
