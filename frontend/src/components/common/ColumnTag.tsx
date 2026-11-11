import type { AssetType } from '../../constants/assetType';

interface Props {
  column: string;
  dataType?: string | null;
  assetName?: string;
  assetType?: AssetType;
  partial?: boolean;
  dark?: boolean;
  onClick?: () => void;
}

/** 方角标签 + 左侧 2px 黄铜竖线；partial 时带问号角标（4 个页面共用）。 */
export function ColumnTag({ column, dataType, assetName, partial, dark, onClick }: Props) {
  return (
    <span
      className={`column-tag ${dark ? 'on-dark' : ''}`}
      title={assetName ? `所属资产：${assetName}` : undefined}
      onClick={onClick}
      style={onClick ? { cursor: 'pointer' } : undefined}
    >
      <span>{column}</span>
      {dataType && <span className="col-type">{dataType}</span>}
      {partial && <span className="partial-mark" title="该列来自 SELECT * 的部分展开，可能缺列">?</span>}
    </span>
  );
}
