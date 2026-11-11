import { useMemo } from 'react';
import { ASSET_TYPE_LABELS, type AssetType } from '../../constants/assetType';
import type { GraphEdge, GraphNode } from '../../types/lineageEdge';
import { layoutGraph } from '../../utils/graphLayout';

interface Props {
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedId?: string | null;
  onNodeSelect?: (node: GraphNode) => void;
  height?: number;
  compact?: boolean;
}

function NodeShape({ type, width, height }: { type: string; width: number; height: number }) {
  if (type === 'view') {
    const cut = 12;
    return (
      <path
        d={`M0 ${cut} L${cut} 0 H${width} V${height} H0 Z`}
        transform="translate(0,0)"
        fill="none"
      />
    );
  }
  return <rect x={0} y={0} width={width} height={height} />;
}

/** <LineageGraph>：/assets/:id 与 /lineage 共用；按 AssetType 分形状、按 EdgeKind/ParseStatus 分线型。 */
export function LineageGraph({ nodes, edges, selectedId, onNodeSelect, height = 480, compact }: Props) {
  const layout = useMemo(() => layoutGraph(nodes, edges), [nodes, edges]);
  const svgHeight = Math.max(height, layout.height);

  if (nodes.length === 0) {
    return (
      <div className="empty-state" style={{ minHeight: 200 }}>
        当前筛选条件下没有可展示的血缘节点。
      </div>
    );
  }

  return (
    <div className="graph-wrap">
      <div className="graph-contours" />
      <svg className="graph-svg" width={layout.width} height={svgHeight} viewBox={`0 0 ${layout.width} ${svgHeight}`}>
        <defs>
          <marker id="arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
            <path d="M0 0 L7 3.5 L0 7 z" fill="color-mix(in oklch, var(--parch) 45%, transparent)" />
          </marker>
          <marker id="arrow-brass" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
            <path d="M0 0 L7 3.5 L0 7 z" fill="var(--brass)" />
          </marker>
        </defs>
        {layout.edges.map((edge, index) => (
          <g key={`${edge.source}-${edge.target}-${index}`}>
            <path
              className={`graph-edge ${edge.edge_kind} ${edge.in_cycle ? 'cycle' : ''} ${
                edge.parse_status === 'partial' ? 'partial' : ''
              } ${edge.in_cycle ? 'edge-anim' : ''}`}
              d={edge.path}
              markerEnd={`url(#${edge.edge_kind === 'aggregate' || edge.edge_kind === 'derived' ? 'arrow-brass' : 'arrow'})`}
              style={edge.in_cycle ? { animationDelay: `${index * 20}ms` } : undefined}
            >
              <title>
                {`${edge.source_column} → ${edge.target_column} · ${edge.transformation_name || ''}${
                  edge.in_cycle ? ' · 环边' : ''
                }`}
              </title>
            </path>
          </g>
        ))}
        {layout.nodes.map((node) => {
          const label = node.column ? node.column : node.asset_name;
          const secondary = node.column
            ? `${node.asset_name} · ${ASSET_TYPE_LABELS[node.asset_type as AssetType] || node.asset_type}`
            : `${ASSET_TYPE_LABELS[node.asset_type as AssetType] || node.asset_type} · ${
                node.column_count ?? 0
              } 列`;
          return (
            <g
              key={node.id}
              transform={`translate(${node.x},${node.y})`}
              className={`graph-node ${selectedId === node.id ? 'selected' : ''}`}
              onClick={() => onNodeSelect?.(node)}
            >
              <g>
                <NodeShape type={node.asset_type} width={node.width} height={node.height} />
              </g>
              <text x={10} y={compact ? 22 : 22}>{label.length > 20 ? `${label.slice(0, 19)}…` : label}</text>
              <text x={10} y={compact ? 36 : 38} className="node-type">
                {secondary.length > 24 ? `${secondary.slice(0, 23)}…` : secondary}
              </text>
              <title>{`${node.asset_name}${node.column ? '.' + node.column : ''} · 深度 ${node.depth}`}</title>
            </g>
          );
        })}
      </svg>
      <div className="graph-legend" style={{ padding: '8px 12px 10px' }}>
        <span>
          <i /> 直传
        </span>
        <span>
          <i className="agg" /> 聚合
        </span>
        <span>
          <i className="der" /> 派生 / partial
        </span>
        <span>
          <i className="cyc" /> 环
        </span>
        <span className="muted">点击节点查看列级边</span>
      </div>
    </div>
  );
}
