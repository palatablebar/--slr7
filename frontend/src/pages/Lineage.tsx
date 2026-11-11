import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { assetsApi } from '../api/assets';
import { lineageApi } from '../api/lineage';
import { CycleWarning } from '../components/common/CycleWarning';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorPanel } from '../components/common/ErrorPanel';
import { LineageGraph } from '../components/common/LineageGraph';
import { AppShell } from '../components/layout/AppShell';
import { AssetInspector } from '../components/layout/AssetInspector';
import { DIRECTION_LABELS, LINEAGE_DIRECTIONS, type LineageDirection } from '../constants/lineageDirection';
import { MSG_EMPTY_LINEAGE } from '../constants/messages';
import type { DataAsset } from '../types/dataAsset';
import type { GraphNode, GraphPayload } from '../types/lineageEdge';

export function LineagePage() {
  const [params, setParams] = useSearchParams();
  const [assets, setAssets] = useState<DataAsset[]>([]);
  const [graph, setGraph] = useState<GraphPayload | null>(null);
  const [startAssetId, setStartAssetId] = useState(params.get('asset') || '');
  const [direction, setDirection] = useState<LineageDirection>('both');
  const [depth, setDepth] = useState(3);
  const [granularity, setGranularity] = useState<'asset' | 'column'>('asset');
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    assetsApi
      .list()
      .then((result) => {
        setAssets(result.items);
        if (!startAssetId && result.items.length > 0) {
          const preferred =
            result.items.find((asset) => asset.display_name === 'ads.gmv_daily') || result.items[0];
          setStartAssetId(preferred.id);
          setParams({ asset: preferred.id });
        }
      })
      .catch(setError);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!startAssetId) return;
    setError(null);
    lineageApi
      .graph({ asset_id: startAssetId, direction, depth, granularity })
      .then((payload) => {
        setGraph(payload);
        const start = payload.nodes.find((node) => node.depth === 0 && node.asset_id === startAssetId);
        setSelectedNode(start || null);
      })
      .catch(setError);
  }, [startAssetId, direction, depth, granularity]);

  const inspectorEdges = useMemo(() => {
    if (!graph || !selectedNode) return [];
    return graph.edges
      .filter((edge) => edge.source === selectedNode.id || edge.target === selectedNode.id)
      .map((edge) => ({
        edge_kind: edge.edge_kind,
        source_column: edge.source_column,
        target_column: edge.target_column,
        expression_text: edge.expression_text,
        transformation_name: edge.transformation_name,
        direction: edge.source === selectedNode.id ? 'downstream' : 'upstream',
      }));
  }, [graph, selectedNode]);

  return (
    <AppShell
      eyebrow="血缘图 / LINEAGE"
      title="列级血缘图探索"
      actions={
        <button type="button" className="btn" onClick={() => {
          setDepth(4);
          setDirection('both');
        }}>
          深度拉满（4 步双向）
        </button>
      }
    >
      <div className="row" style={{ marginBottom: 12, gap: 14 }}>
        <div className="field" style={{ minWidth: 220 }}>
          <label>起点资产</label>
          <select
            className="select"
            value={startAssetId}
            onChange={(event) => {
              setStartAssetId(event.target.value);
              setParams({ asset: event.target.value });
              setSelectedNode(null);
            }}
          >
            {assets.map((asset) => (
              <option key={asset.id} value={asset.id}>
                {asset.display_name}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>方向</label>
          <div className="seg">
            {LINEAGE_DIRECTIONS.map((item) => (
              <button key={item} className={direction === item ? 'on' : ''} onClick={() => setDirection(item)}>
                {DIRECTION_LABELS[item]}
              </button>
            ))}
          </div>
        </div>
        <div className="field">
          <label>深度 {depth} 步</label>
          <div className="seg">
            {[1, 2, 3, 4].map((item) => (
              <button key={item} className={depth === item ? 'on' : ''} onClick={() => setDepth(item)}>
                {item}
              </button>
            ))}
          </div>
        </div>
        <div className="field">
          <label>粒度</label>
          <div className="seg">
            <button className={granularity === 'asset' ? 'on' : ''} onClick={() => setGranularity('asset')}>
              资产级
            </button>
            <button className={granularity === 'column' ? 'on' : ''} onClick={() => setGranularity('column')}>
              列级
            </button>
          </div>
        </div>
        <span style={{ flex: 1 }} />
        {graph && (
          <span className="mono small muted">
            {graph.nodes.length} 节点 · {graph.edges.length} 边
            {graph.cycles && graph.cycles.length > 0 ? ' · 有环' : ''}
          </span>
        )}
      </div>
      <ErrorPanel error={error} />
      {graph && graph.cycles && graph.cycles.length > 0 && <CycleWarning cycles={graph.cycles} />}
      <div className="canvas-first">
        <div style={{ padding: 12 }}>
          {graph && graph.nodes.length > 0 ? (
            <LineageGraph
              nodes={graph.nodes}
              edges={graph.edges}
              selectedId={selectedNode?.id}
              onNodeSelect={(node) => setSelectedNode(node)}
              height={560}
            />
          ) : (
            <EmptyState title="还没有血缘图" hint={MSG_EMPTY_LINEAGE} sampleSql />
          )}
        </div>
        <AssetInspector
          title={selectedNode ? selectedNode.asset_name : graph?.start_asset?.name}
          column={selectedNode?.column || undefined}
          edges={inspectorEdges}
        />
      </div>
      <div className="small muted" style={{ marginTop: 10 }}>
        {graph?.truncated
          ? '结果被深度上限截断，请缩小范围或降低深度。'
          : '图中 partial 转换的边会以半透明虚线呈现；环边用橙色虚线标出。'}
      </div>
    </AppShell>
  );
}
