/** 从 SQL 中按列名定位相关片段并给出高亮区间。 */
export function findColumnSnippet(sql: string, column: string, radius = 110) {
  if (!sql || !column) return { snippet: sql?.slice(0, 200) || '', start: 0, end: 0 };
  const index = sql.toLowerCase().indexOf(column.toLowerCase());
  if (index < 0) return { snippet: sql.slice(0, 200), start: 0, end: 0 };
  const start = Math.max(0, index - radius);
  const end = Math.min(sql.length, index + column.length + radius);
  return {
    snippet: `${start > 0 ? '…' : ''}${sql.slice(start, end).trim()}${end < sql.length ? '…' : ''}`,
    start,
    end,
  };
}

export function minimalReplaceSnippet(column: string, action: string) {
  if (action === 'add_cast') return `CAST(${column} AS numeric(18,2))`;
  if (action === 'refresh_mv') return `REFRESH MATERIALIZED VIEW <schema>.<mv_name>;`;
  if (action === 'drop_downstream') return `-- remove ${column} from SELECT`;
  return `-- rewrite expression referencing ${column}`;
}
