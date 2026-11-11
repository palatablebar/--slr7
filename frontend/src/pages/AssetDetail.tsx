import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { assetsApi } from '../api/assets';
import { AssetBadge } from '../components/common/AssetBadge';
import { ColumnTag } from '../components/common/ColumnTag';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorPanel } from '../components/common/ErrorPanel';
import { LineageGraph } from '../components/common/LineageGraph';
import { AppShell } from '../components/layout/AppShell';
import { AssetInspector } from '../components/layout/AssetInspector';
import { CHANGE_TYPE_LABELS, type ChangeType } from '../constants/changeType';
import { EDGE_KIND_LABELS, type EdgeKind } from '../constants/edgeKind';
import { MSG_PARTIAL_HINT } from '../constants/messages';
import { useAuthStore } from '../stores/authStore';
import type { AssetDetail } from '../types/dataAsset';
import type { GraphEdge, GraphNode } from '../types/lineageEdge';
import { formatDateTime } from '../utils/formatCount';

export function AssetDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isAnalyst = useAuthStore((state) => state.isAnalystOrAbove());
  const [asset, setAsset] = useState<AssetDetail | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [selectedColumn, setSelectedColumn] = useState<string | null>(null);
  const [newColumn, setNewColumn] = useState('');
  const [newType, setNewType] = useState('varchar(64)');
  const [saving, setSaving] = useState(false);

  const load = () => {
    if (!id) return;
    assetsApi.detail(id).then(setAsset).catch(setError);
  };
  useEffect(load, [id]);

  const graph = useMemo(() => {
    if (!asset) return { nodes: [] as GraphNode[], edges: [] as GraphEdge[] };
    const nodes: GraphNode[] = [
      {
        id: asset.id,
        asset_id: asset.id,
        asset_name: asset.display_name,
        asset_type: asset.asset_type,
        depth: 1,
        column_count: asset.column_count,
      },
    ];
    const edges: GraphEdge[] = [];
    const seen = new Set<string>([asset.id]);
    asset.upstream_assets.forEach((edge) => {
      if (!seen.has(edge.asset_id)) {
        seen.add(edge.asset_id);
        nodes.push({
          id: edge.asset_id,
          asset_id: edge.asset_id,
          asset_name: edge.asset_name,
          asset_type: edge.asset_type,
          depth: 0,
        });
      }
      edges.push({
        source: edge.asset_id,
        target: asset.id,
        edge_kind: edge.edge_kind as EdgeKind,
        source_column: edge.source_column,
        target_column: edge.target_column,
        expression_text: edge.expression_text,
      });
    });
    asset.downstream_assets.forEach((edge) => {
      if (!seen.has(edge.asset_id)) {
        seen.add(edge.asset_id);
        nodes.push({
          id: edge.asset_id,
          asset_id: edge.asset_id,
          asset_name: edge.asset_name,
          asset_type: edge.asset_type,
          depth: 2,
        });
      }
      edges.push({
        source: asset.id,
        target: edge.asset_id,
        edge_kind: edge.edge_kind as EdgeKind,
        source_column: edge.source_column,
        target_column: edge.target_column,
        expression_text: edge.expression_text,
      });
    });
    return { nodes, edges };
  }, [asset]);

  const inspectorEdges = useMemo(() => {
    if (!asset) return [];
    const list = [...asset.upstream_assets, ...asset.downstream_assets];
    return list
      .filter((edge) => !selectedColumn || edge.source_column === selectedColumn || edge.target_column === selectedColumn)
      .map((edge) => ({
        edge_kind: edge.edge_kind,
        source_column: edge.source_column,
        target_column: edge.target_column,
        expression_text: edge.expression_text,
        transformation_name: asset.producer_transformations.find((t) => t.id === edge.transformation_id)?.name,
        direction: asset.upstream_assets.includes(edge) ? 'upstream' : 'downstream',
      }));
  }, [asset, selectedColumn]);

  const addColumn = async () => {
    if (!asset || !id || !newColumn.trim()) return;
    setSaving(true);
    try {
      const columns = [
        ...(asset.columns || []).map((column) => ({
          name: column.name,
          data_type: column.data_type,
          nullable: column.nullable,
          ordinal: column.ordinal,
          description: column.description,
        })),
        { name: newColumn.trim(), data_type: newType, nullable: true, ordinal: (asset.columns?.length || 0) + 1 },
      ];
      await assetsApi.update(id, { columns_json: columns });
      setNewColumn('');
      load();
    } catch (err) {
      setError(err);
    } finally {
      setSaving(false);
    }
  };

  if (!asset) {
    return (
      <AppShell eyebrow="资产详情" title="资产详情">
        <ErrorPanel error={error} />
        {!error && <div className="small muted">加载中…</div>}
      </AppShell>
    );
  }

  return (
    <AppShell
      eyebrow={`资产详情 / ${asset.full_name}`}
      title={asset.display_name}
      actions={
        <button type="button" className="btn" onClick={() => navigate(`/lineage?asset=${asset.id}`)}>
          在图探索中打开
        </button>
      }
    >
      <div className="row" style={{ marginBottom: 12 }}>
        <AssetBadge database={asset.database_name} schema={asset.schema_name} assetType={asset.asset_type} status={asset.status} />
        <span className="mono small muted">{asset.column_count} 列</span>
        <span className="mono small muted">owner：{asset.owner_display_name || '—'}</span>
        <span className="small muted">{asset.description}</span>
      </div>
      <div className="canvas-first">
        <div className="stack" style={{ padding: 14 }}>
          <div className="panel-title" style={{ color: 'var(--brass)' }}>
            一跳上下游
          </div>
          <LineageGraph
            nodes={graph.nodes}
            edges={graph.edges}
            height={300}
            selectedId={selectedColumn ? undefined : undefined}
            onNodeSelect={(node) => navigate(`/assets/${node.asset_id}`)}
          />
        </div>
        <AssetInspector
          title={selectedColumn ? `${asset.display_name}.${selectedColumn}` : asset.display_name}
          column={selectedColumn}
          sqlText={asset.description || ''}
          edges={inspectorEdges}
        />
      </div>

      <hr className="section-rule" />
      <div className="panel">
        <div className="spread" style={{ marginBottom: 10 }}>
          <span className="panel-title">列清单</span>
          <span className="small muted">点击列名只看该列血缘</span>
        </div>
        <table className="data-table dark">
          <thead>
            <tr>
              <th>列名</th>
              <th>类型</th>
              <th>可空</th>
              <th>描述</th>
              <th>上游数</th>
              <th>下游数</th>
            </tr>
          </thead>
          <tbody>
            {asset.columns.map((column) => (
              <tr key={column.name}>
                <td>
                  <ColumnTag
                    column={column.name}
                    dataType={column.data_type}
                    dark
                    onClick={() => setSelectedColumn(column.name)}
                  />
                </td>
                <td className="mono">{column.data_type || '—'}</td>
                <td className="small">{column.nullable ? '是' : '否'}</td>
                <td className="small muted">{column.description || '—'}</td>
                <td className="mono">{column.upstream_count ?? 0}</td>
                <td className="mono">{column.downstream_count ?? 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="row" style={{ marginTop: 12 }}>
          <input
            className="input"
            placeholder="补登记列名，例如 pay_method"
            value={newColumn}
            onChange={(event) => setNewColumn(event.target.value)}
            style={{ width: 220 }}
          />
          <input className="input" value={newType} onChange={(event) => setNewType(event.target.value)} style={{ width: 150 }} />
          <button type="button" className="btn" disabled={!isAnalyst || saving || !newColumn.trim()} onClick={addColumn}>
            登记变更
          </button>
          {!isAnalyst && <span className="small muted">viewer 只读</span>}
        </div>
        <div className="small muted" style={{ marginTop: 8 }}>
          {MSG_PARTIAL_HINT}
        </div>
      </div>

      <hr className="section-rule" />
      <div className="panel">
        <div className="panel-title" style={{ marginBottom: 10 }}>
          结构变更时间线
        </div>
        {asset.schema_changes.length === 0 && <div className="small muted">暂无结构变更记录。</div>}
        <div className="stack">
          {asset.schema_changes.map((change) => (
            <div key={change.id} className="spread" style={{ borderLeft: '1px solid var(--brass)', paddingLeft: 12 }}>
              <div>
                <div className="mono">
                  {change.column_name} · {CHANGE_TYPE_LABELS[change.change_type as ChangeType] || change.change_type}
                </div>
                <div className="small muted">
                  {change.old_type || '—'} → {change.new_type || '—'} · 来源 {change.source}
                </div>
              </div>
              <span className="mono small muted">{formatDateTime(change.detected_at)}</span>
            </div>
          ))}
        </div>
      </div>

      <hr className="section-rule" />
      <div className="cols-2">
        <div className="panel">
          <div className="eyebrow">产出该资产的转换</div>
          <div className="stack" style={{ marginTop: 8 }}>
            {asset.producer_transformations.length === 0 && <div className="small muted">暂无</div>}
            {asset.producer_transformations.map((item) => (
              <div key={item.id} className="spread">
                <span className="mono small">{item.name}</span>
                <span className={`badge ${item.parse_status === 'parsed' ? 'ok' : 'warn'}`}>{item.parse_status}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="panel">
          <div className="eyebrow">引用该资产的转换</div>
          <div className="stack" style={{ marginTop: 8 }}>
            {asset.consumer_transformations.length === 0 && <div className="small muted">暂无</div>}
            {asset.consumer_transformations.map((item) => (
              <div key={item.id} className="spread">
                <span className="mono small">{item.name}</span>
                <span className={`badge ${item.parse_status === 'parsed' ? 'ok' : 'warn'}`}>{item.parse_status}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
      <ErrorPanel error={error} />
    </AppShell>
  );
}
