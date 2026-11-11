import { useEffect, useMemo, useState } from 'react';
import { assetsApi } from '../api/assets';
import { transformationsApi } from '../api/transformations';
import { AssetBadge } from '../components/common/AssetBadge';
import { ColumnTag } from '../components/common/ColumnTag';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorPanel } from '../components/common/ErrorPanel';
import { SqlEditor } from '../components/common/SqlEditor';
import { AppShell } from '../components/layout/AppShell';
import { EDGE_KIND_LABELS, type EdgeKind } from '../constants/edgeKind';
import {
  MSG_DRAFT_DISCARDED,
  MSG_PARSE_FAILED_ADVICE,
  MSG_PARTIAL_HINT,
} from '../constants/messages';
import { PARSE_STATUS_LABELS, type ParseStatus } from '../constants/parseStatus';
import { useAuthStore } from '../stores/authStore';
import type { DataAsset } from '../types/dataAsset';
import type { ParsePreview } from '../types/parse';
import type { Transformation, TransformationDraft } from '../types/transformation';

interface SaveNotice {
  promoted: boolean;
  message: string;
}

export function TransformationsPage() {
  const isAnalyst = useAuthStore((state) => state.isAnalystOrAbove());
  const [items, setItems] = useState<Transformation[]>([]);
  const [selected, setSelected] = useState<Transformation | null>(null);
  const [sqlDraft, setSqlDraft] = useState('');
  const [preview, setPreview] = useState<ParsePreview | null>(null);
  const [assets, setAssets] = useState<DataAsset[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [workerMsg, setWorkerMsg] = useState('');
  const [saveNotice, setSaveNotice] = useState<SaveNotice | null>(null);

  useEffect(() => {
    transformationsApi
      .list()
      .then((result) => {
        setItems(result.items);
        if (result.items.length > 0) {
          openTransformation(result.items[0].id);
        }
      })
      .catch(setError);
    assetsApi.list().then((result) => setAssets(result.items)).catch(() => undefined);
  }, []);

  const openTransformation = async (id: string) => {
    try {
      const detail = await transformationsApi.detail(id);
      setSelected(detail);
      // 有未上线草稿时优先打开草稿内容（包括解析失败的错误 SQL），否则打开上线版本
      setSqlDraft(detail.draft ? detail.draft.sql_text : detail.sql_text);
      setPreview(null);
      setWorkerMsg('');
      setSaveNotice(null);
    } catch (err) {
      setError(err);
    }
  };

  const outputAsset = useMemo(
    () => assets.find((asset) => asset.id === selected?.output_asset_id),
    [assets, selected],
  );

  const draft: TransformationDraft | null = selected?.draft ?? null;
  const publishedStatus: ParseStatus = (selected?.parse_status || 'pending') as ParseStatus;
  const draftStatus: ParseStatus | null = draft ? (draft.parse_status as ParseStatus) : null;
  const report = selected?.report_json || {};
  const unresolved = (report.unresolved || []) as any[];
  const warnings = ((draft?.report_json?.warnings as string[] | undefined) ??
    (report.warnings as string[] | undefined) ??
    []) as string[];

  const refreshList = async () => {
    const list = await transformationsApi.list();
    setItems(list.items);
  };

  const saveAndParse = async () => {
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      const result = await transformationsApi.update(selected.id, { sql_text: sqlDraft });
      setSelected(result.transformation);
      setSaveNotice({ promoted: result.promoted, message: result.message });
      // 发布成功后编辑器对齐新上线 SQL；失败时保留草稿原文（即用户输入的错误内容）
      setSqlDraft(result.transformation.draft ? result.transformation.draft.sql_text : result.transformation.sql_text);
      await refreshList();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  const discardDraft = async () => {
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      const detail = await transformationsApi.discardDraft(selected.id);
      setSelected(detail);
      setSqlDraft(detail.sql_text);
      setPreview(null);
      setSaveNotice({ promoted: true, message: MSG_DRAFT_DISCARDED });
      await refreshList();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  const runPreview = async () => {
    if (!selected) return;
    setBusy(true);
    try {
      const result = await transformationsApi.preview(selected.id, sqlDraft);
      setPreview(result);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  const enqueue = async () => {
    if (!selected) return;
    setBusy(true);
    try {
      const result = await transformationsApi.enqueueParse(selected.id);
      setWorkerMsg(`已投递 Celery（queue=${result.queue}, task=${result.task_id.slice(0, 8)}…）`);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AppShell eyebrow="转换解析 / TRANSFORMATIONS" title="SQL 转换与解析">
      <div style={{ display: 'grid', gridTemplateColumns: '260px minmax(0, 1fr)', gap: 16 }}>
        <div className="panel" style={{ padding: 0, overflow: 'hidden' }}>
          <div className="eyebrow" style={{ padding: '12px 12px 6px' }}>
            转换清单 · {items.length}
          </div>
          <div style={{ maxHeight: 640, overflow: 'auto' }}>
            {items.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => openTransformation(item.id)}
                style={{
                  display: 'block',
                  width: '100%',
                  textAlign: 'left',
                  background: selected?.id === item.id ? 'var(--brass-soft)' : 'transparent',
                  border: 0,
                  borderLeft: `2px solid ${selected?.id === item.id ? 'var(--brass)' : 'transparent'}`,
                  borderBottom: '1px solid var(--deep-line)',
                  padding: '9px 12px',
                  cursor: 'pointer',
                }}
              >
                <div className="mono small" style={{ color: 'var(--parch)' }}>
                  {item.name}
                </div>
                <div className="row" style={{ marginTop: 4 }}>
                  <span className={`badge ${item.parse_status === 'parsed' ? 'ok' : item.parse_status === 'failed' ? 'warn' : ''}`}>
                    {PARSE_STATUS_LABELS[item.parse_status as ParseStatus]}
                  </span>
                  <span className="badge">{item.edge_count} 边</span>
                  <span className="badge">v{item.version}</span>
                  {item.has_draft && (
                    <span className={`badge ${item.draft?.parse_status === 'failed' ? 'warn' : 'brass'}`}>
                      草稿{item.draft ? PARSE_STATUS_LABELS[item.draft.parse_status as ParseStatus] : ''}
                    </span>
                  )}
                </div>
              </button>
            ))}
          </div>
        </div>

        <div>
          <ErrorPanel error={error} />
          {!selected && <EmptyState title="还没有转换" hint="先录入一段 SQL。" />}
          {selected && (
            <>
              <div className="row" style={{ marginBottom: 10, gap: 10 }}>
                <span className="panel-title">{selected.name}</span>
                <span className={`badge ${publishedStatus === 'parsed' ? 'ok' : publishedStatus === 'failed' ? 'warn' : 'brass'}`}>
                  上线：{PARSE_STATUS_LABELS[publishedStatus]}
                </span>
                {draft && (
                  <span className={`badge ${draftStatus === 'failed' ? 'warn' : 'brass'}`}>
                    草稿：{PARSE_STATUS_LABELS[draftStatus as ParseStatus]}
                  </span>
                )}
                <span className="badge">方言 {selected.dialect}</span>
                <span className="badge">v{selected.version}</span>
                <span style={{ flex: 1 }} />
                {outputAsset && (
                  <AssetBadge
                    database={outputAsset.database_name}
                    schema={outputAsset.schema_name}
                    assetType={outputAsset.asset_type}
                  />
                )}
              </div>
              <div className="split-55-45">
                <SqlEditor
                  value={sqlDraft}
                  onChange={setSqlDraft}
                  errorLine={draftStatus === 'failed' ? draft?.error_line : preview?.error_line}
                  readOnly={!isAnalyst}
                  statusLabel={draft ? `草稿·${PARSE_STATUS_LABELS[draftStatus as ParseStatus]}` : PARSE_STATUS_LABELS[publishedStatus]}
                />
                <div className="parse-pane">
                  <div className="row" style={{ gap: 8, marginBottom: 10 }}>
                    <button type="button" className="btn btn-primary" disabled={!isAnalyst || busy} onClick={saveAndParse}>
                      保存草稿并校验
                    </button>
                    <button type="button" className="btn" disabled={!isAnalyst || busy} onClick={runPreview}>
                      试解析（不落库）
                    </button>
                    <button type="button" className="btn" disabled={!isAnalyst || busy || !draft} onClick={discardDraft}>
                      丢弃草稿
                    </button>
                    <button type="button" className="btn" disabled={!isAnalyst || busy} onClick={enqueue}>
                      投递 Worker
                    </button>
                  </div>
                  {saveNotice && (
                    <div className={`notice small ${saveNotice.promoted ? 'ok' : 'warn'}`}>
                      {saveNotice.message}
                    </div>
                  )}
                  {workerMsg && <div className="notice small">{workerMsg}</div>}
                  {draft && (
                    <div className="notice small" style={{ marginTop: 8 }}>
                      正在编辑未上线草稿；右侧列映射与血缘图始终展示<strong>已上线版本 v{selected.version}</strong>
                      ，草稿通过校验后才会一次性切换。
                    </div>
                  )}
                  <hr className="section-rule" />
                  <div className="eyebrow">输入资产 / 输出资产</div>
                  <div className="row" style={{ marginTop: 6, marginBottom: 10 }}>
                    {(selected.input_assets || []).map((asset) => (
                      <span key={asset.id} className="badge">
                        {asset.name}
                      </span>
                    ))}
                    <span className="muted small">→</span>
                    <span className="badge brass">{selected.output_asset_name}</span>
                  </div>
                  {draftStatus === 'failed' && draft?.parse_error && (
                    <div className="notice warn small">
                      <strong>草稿解析失败（已上线血缘与影响分析未受影响）</strong>
                      <div style={{ marginTop: 4 }}>{draft.parse_error.split('\n')[0]}</div>
                      <div className="mono small" style={{ marginTop: 6, whiteSpace: 'pre-wrap' }}>
                        {draft.parse_error}
                      </div>
                      {(draft.error_line || draft.error_column) && (
                        <div className="small muted" style={{ marginTop: 4 }}>
                          出错位置：第 {draft.error_line ?? '?'} 行，第 {draft.error_column ?? '?'} 列（编辑器已高亮）
                        </div>
                      )}
                      <div className="small muted" style={{ marginTop: 6 }}>
                        错误 SQL 已保留在草稿中，可直接修改后重新保存，或点「丢弃草稿」恢复上线版本。{MSG_PARSE_FAILED_ADVICE}
                      </div>
                    </div>
                  )}
                  {draftStatus === 'partial' && (
                    <div className="notice warn small">
                      <div>
                        <strong>草稿部分解析：</strong>
                        {((draft?.report_json?.unresolved as any[] | undefined) || [])
                          .map((item) => item.missing?.join('、') || item.column || item.reason)
                          .join('；') || '存在未展开的列'}
                      </div>
                      <div className="small muted" style={{ marginTop: 4 }}>
                        {MSG_PARTIAL_HINT}
                      </div>
                    </div>
                  )}
                  {!draft && publishedStatus === 'failed' && (
                    <div className="notice warn small">
                      <strong>{selected.parse_error?.split('\n')[0] || '解析失败'}</strong>
                      <div className="mono small" style={{ marginTop: 6, whiteSpace: 'pre-wrap' }}>
                        {selected.parse_error}
                      </div>
                      <div className="small muted" style={{ marginTop: 6 }}>
                        {MSG_PARSE_FAILED_ADVICE}
                      </div>
                    </div>
                  )}
                  {!draft && publishedStatus === 'partial' && (
                    <div className="notice warn small">
                      <div>
                        <strong>部分解析：</strong>
                        {(unresolved.map((item) => item.missing?.join('、') || item.column || item.reason).join('；')) ||
                          '存在未展开的列'}
                      </div>
                      <div className="small muted" style={{ marginTop: 4 }}>
                        {MSG_PARTIAL_HINT}
                      </div>
                    </div>
                  )}
                  {warnings.length > 0 && (
                    <div className="small muted" style={{ marginTop: 8 }}>
                      warnings：{warnings.join('；')}
                    </div>
                  )}
                  <hr className="section-rule" />
                  <div className="eyebrow">
                    列映射 · 已上线版本（{selected.edges?.length || 0} 条边{draft ? '，草稿未发布前保持不变' : ''}）
                  </div>
                  <table className="data-table dark" style={{ marginTop: 6 }}>
                    <thead>
                      <tr>
                        <th>目标列</th>
                        <th>来源列</th>
                        <th>边类型</th>
                        <th>表达式</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(selected.edges || []).map((edge) => (
                        <tr key={edge.id}>
                          <td>
                            <ColumnTag
                              column={edge.target_column}
                              dark
                              partial={publishedStatus === 'partial' && edge.source_column === '*'}
                            />
                          </td>
                          <td className="mono small">
                            {(assets.find((asset) => asset.id === edge.source_asset_id)?.display_name || '') +
                              '.' +
                              edge.source_column}
                          </td>
                          <td>
                            <span className="badge brass">{EDGE_KIND_LABELS[edge.edge_kind as EdgeKind]}</span>
                          </td>
                          <td className="mono small" style={{ maxWidth: 260, wordBreak: 'break-all' }}>
                            {edge.expression_text || '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {report.columns?.length > 0 && (
                    <div className="small muted" style={{ marginTop: 10 }}>
                      解析器：{report.parser} · 方言 {report.dialect} · {report.star_expanded ? '含 SELECT * 展开' : '无星号展开'}
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </AppShell>
  );
}
