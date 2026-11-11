import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { assetsApi } from '../api/assets';
import { AssetBadge } from '../components/common/AssetBadge';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorPanel } from '../components/common/ErrorPanel';
import { ASSET_TYPES, ASSET_TYPE_LABELS, type AssetType } from '../constants/assetType';
import { MSG_EMPTY_ASSET } from '../constants/messages';
import { AppShell } from '../components/layout/AppShell';
import { useAssetStore } from '../stores/assetStore';
import type { DataAsset } from '../types/dataAsset';

export function AssetsPage() {
  const navigate = useNavigate();
  const { assets, groups, setList, loading, setLoading } = useAssetStore();
  const [query, setQuery] = useState('');
  const [assetType, setAssetType] = useState<string>('');
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    assetsApi
      .list({ q: query || undefined, asset_type: assetType || undefined })
      .then((result) => setList(result.items, result.groups))
      .catch(setError)
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query, assetType]);

  const counts = useMemo(() => {
    const map: Record<string, number> = {};
    assets.forEach((asset) => {
      const key = `${asset.database_name}.${asset.schema_name}`;
      map[key] = (map[key] || 0) + 1;
    });
    return map;
  }, [assets]);

  return (
    <AppShell eyebrow="资产目录 / ASSETS" title="资产目录">
      <div className="row" style={{ marginBottom: 14, gap: 12 }}>
        <input
          className="input"
          placeholder="按资产名或列名搜索…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          style={{ width: 280 }}
        />
        <div className="seg">
          <button className={assetType === '' ? 'on' : ''} onClick={() => setAssetType('')}>
            全部
          </button>
          {ASSET_TYPES.map((type) => (
            <button key={type} className={assetType === type ? 'on' : ''} onClick={() => setAssetType(type)}>
              {ASSET_TYPE_LABELS[type as AssetType]}
            </button>
          ))}
        </div>
        <span style={{ flex: 1 }} />
        <span className="mono small muted">
          共 {assets.length} 个资产 · {Object.keys(counts).length} 个库
        </span>
      </div>
      <ErrorPanel error={error} />
      {!loading && assets.length === 0 && (
        <EmptyState title="资产目录为空" hint={MSG_EMPTY_ASSET} actionLabel="登记资产" onAction={() => navigate('/transformations')} />
      )}
      {Object.entries(groups).map(([group, items]) => (
        <section key={group} style={{ marginBottom: 20 }}>
          <div className="spread" style={{ borderBottom: '1px solid var(--deep-line)', paddingBottom: 6 }}>
            <span className="eyebrow">
              {group} · {items.length} 个资产
            </span>
            <span className="mono small muted">{items.reduce((sum, item) => sum + (item.column_count || 0), 0)} 列</span>
          </div>
          <table className="data-table dark">
            <thead>
              <tr>
                <th>资产</th>
                <th>类型</th>
                <th>列数</th>
                <th>血缘边</th>
                <th>状态</th>
                <th>说明</th>
              </tr>
            </thead>
            <tbody>
              {items.map((asset: DataAsset) => (
                <tr key={asset.id} style={{ cursor: 'pointer' }} onClick={() => navigate(`/assets/${asset.id}`)}>
                  <td>
                    <div className="mono" style={{ color: 'var(--parch)' }}>
                      {asset.display_name}
                    </div>
                    <div className="small muted">{asset.full_name}</div>
                  </td>
                  <td>
                    <AssetBadge
                      database={asset.database_name}
                      schema={asset.schema_name}
                      assetType={asset.asset_type}
                    />
                  </td>
                  <td className="mono">{asset.column_count}</td>
                  <td className="mono">{(asset as any).edge_count ?? 0}</td>
                  <td className="small">{asset.status === 'active' ? '启用' : asset.status}</td>
                  <td className="small muted" style={{ maxWidth: 340 }}>
                    {asset.description || '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ))}
    </AppShell>
  );
}
