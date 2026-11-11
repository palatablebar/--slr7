export const MSG_EMPTY_ASSET = '还没有资产。先登记一张表资产，例如 ods.orders。';
export const MSG_EMPTY_LINEAGE = '先选一个起点资产，或从资产目录挑一个。';
export const MSG_NO_DOWNSTREAM = '该列没有下游引用，变更不会影响其它资产。';
export const MSG_VIEWER_FORBIDDEN =
  '报表 owner（viewer）只读：不能发起影响分析，请使用数据开发（analyst）账号。';
export const MSG_PARTIAL_HINT =
  '补全上游列清单后重解析：到 /assets/:id 用「登记变更」补上缺失列，再回到本页点「重新解析」。';
export const MSG_PARSE_FAILED_ADVICE =
  '确认 SQL 语法与方言；如果是方言差异，把 dialect 从 postgres 改成 snowflake 再试一次。';
export const MSG_DRAFT_SAVED_FAILED =
  '草稿已保存，但 SQL 解析未通过：错误内容留在草稿中，已上线版本的列级血缘与影响分析保持不变。';
export const MSG_DRAFT_PROMOTED = '草稿解析通过，已一次性切换为新的上线版本（血缘边整体替换，无中间状态）。';
export const MSG_DRAFT_BUSY = '草稿仍未通过解析校验，不能发布；请修正 SQL 后重新保存。';
export const MSG_DRAFT_DISCARDED = '草稿已丢弃，恢复到当前上线版本。';
export const SAMPLE_SQL = `SELECT o.order_id,
       SUM(o.amount) AS gmv
FROM ods.orders AS o
GROUP BY o.order_id`;
