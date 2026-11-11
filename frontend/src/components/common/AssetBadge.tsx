import { ASSET_TYPE_LABELS, type AssetType } from '../../constants/assetType';

interface Props {
  database?: string;
  schema: string;
  assetType: AssetType;
  status?: string;
}

/** 小方角标签：显示 database.schema 与 AssetType（/assets 与 /transformations 共用）。 */
export function AssetBadge({ database = 'lanzo_dw', schema, assetType, status }: Props) {
  return (
    <span className="row" style={{ gap: 6 }}>
      <span className="badge">
        {database}.{schema}
      </span>
      <span className={`badge ${assetType === 'cte_result' ? 'warn' : 'brass'}`}>
        {ASSET_TYPE_LABELS[assetType] || assetType}
      </span>
      {status && status !== 'active' && <span className="badge warn">{status === 'deprecated' ? '废弃' : '草稿'}</span>}
    </span>
  );
}
