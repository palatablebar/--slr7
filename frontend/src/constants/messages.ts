export const MSG_EMPTY_ASSET = '还没有资产。先登记一张表资产，例如 ods.orders。';
export const MSG_EMPTY_LINEAGE = '先选一个起点资产，或从资产目录挑一个。';
export const MSG_NO_DOWNSTREAM = '该列没有下游引用，变更不会影响其它资产。';
export const MSG_VIEWER_FORBIDDEN =
  '报表 owner（viewer）只读：不能发起影响分析，请使用数据开发（analyst）账号。';
export const MSG_PARTIAL_HINT =
  '补全上游列清单后重解析：到 /assets/:id 用「登记变更」补上缺失列，再回到本页点「重新解析」。';
export const MSG_PARSE_FAILED_ADVICE =
  '确认 SQL 语法与方言；如果是方言差异，把 dialect 从 postgres 改成 snowflake 再试一次。';
export const SAMPLE_SQL = `SELECT o.order_id,
       SUM(o.amount) AS gmv
FROM ods.orders AS o
GROUP BY o.order_id`;
