# DataTrace · 列级数据血缘与影响分析平台

**登记资产与 SQL → 用 sqlglot 解析到列 → 查血缘 → 算影响**：把数仓里"某个字段从哪来、改掉它谁会坏"从 wiki 手绘和口头通知，变成一条可回看的列级血缘链与一份带建议 SQL 的迁移清单。

---

## 快速启动

```bash
cp .env.example .env
docker compose up -d
# 等 5 个容器 healthy（约 40~70 秒）
docker compose ps
```

- 前端：<http://localhost:18115>
- 后端 API 文档：<http://localhost:19115/docs>
- 演示账号（密码均为 `Demo@2026`）：

| 账号 | 角色 | 能做什么 |
|---|---|---|
| `admin@datatrace.local` | `admin` 平台管理员 | 全部读写；可删资产、改他人转换 |
| `analyst@datatrace.local` | `analyst` 数据开发 | 登记资产、提交/修改 SQL、发起影响分析 |
| `viewer@datatrace.local` | `viewer` 报表 owner | 只读；**不能发起影响分析**（403 + `E_FORBIDDEN`） |

> 首次启动时 backend 的 lifespan 会在 `SEED_DEMO=true` 时自动执行一次 seed（失败只记 `SEED_FAILED` 日志，不阻塞启动）。

### 演示数据初始化（seed 幂等）

```bash
docker compose exec backend python -m scripts.seed_demo
```

该命令**可重复执行**：资产按 `(database_name, schema_name, name)`、转换按 `name`、边按 `(transformation_id, source_column, target_column)` 去重；重复执行不新增资产/边、不重算已 `parsed` 的 SQL、不改写历史 `ImpactAnalysis`。

执行后应得到：

- **3 个账号**：admin / analyst / viewer（见上表）
- **5 个资产**（4 张业务表 + 1 个 `cte_result` 资产，按 `lanzo_dw.<schema>.<name>` 登记）：
  - `ods.orders`（5 列）
  - `dwd.order_detail`（4 列；**故意少登记 `pay_method`**，这是 `SELECT *` 判成 `partial` 的坑）
  - `dws.user_gmv`（3 列）
  - `ads.gmv_daily`（5 列）
  - `dwd.cte_result`（`asset_type=cte_result`，计入影响面但不进迁移清单）
- **6 段 SQL**：5 段 `parsed` + 1 段 `partial`（`t06_star_partial_from_order_detail`，`SELECT * FROM dwd.order_detail`）
- **1 次历史 `SchemaChangeEvent`**：`dwd.order_detail.pay_amount`，`decimal(18,2)` → `string`，`source=manual`
- **1 条历史 `ImpactAnalysis`**：目标 `dwd.order_detail.pay_amount`、`change_type=change_type`、`severity=high`、`affected_count=5`

主链 `ods.orders → dwd.order_detail → dws.user_gmv → ads.gmv_daily` 由 seed 触发真实解析产出（脚本内**不手写任何边**）。

---

## 典型使用场景（模拟客户：岚舟科技数据平台）

岚舟科技 800 人、数仓 300+ 张表、5 个团队各自维护 nightly SQL。上一次事故：上游把 `pay_amount` 从 `decimal` 改成 `string`，3 张报表静默出错，排查了两天——因为没人说得清 `pay_amount` 流经哪几段 SQL、被哪几列 `SUM` 过。

现在的流程：

1. 平台管理员在 `/assets` 登记 `ods.orders`、`dwd.order_detail`（`pay_amount` = `decimal(18,2)`）、`dws.user_gmv`、`ads.gmv_daily`，`dwd.order_detail` 故意少登记 1 列（`pay_method`）；
2. 在 `/transformations` 录入 6 段 SQL（CTE / 子查询 / 多输入 JOIN / `SUM` 聚合 / `CAST` 表达式 / `SELECT *`），解析后 5 段 `parsed`、1 段 `partial`；
3. 数据开发要把 `dwd.order_detail.pay_amount` 改成 `string`，先在 `/impact` 发起分析：报告给出 **`high`、3 个资产 / 5 个列 / 2 张报表**，迁移清单分 `add_cast` / `rewrite_sql` 两类，每条带 `suggested_sql`；
4. 导出 `report_json.migration_checklist` 发给报表 owner；owner 用 `viewer` 账号只读确认（发起分析会被 403 拒绝）；
5. 出问题时可回 `/assets/:id` 看 `pay_amount` 的结构变更时间线，或到 `/lineage` 从 `ads.gmv_daily` 往上游走 3 步抽查列级链。

---

## 主要功能

- **资产与列清单**：`/assets` 按 `database.schema` 分组折叠、按类型筛选、按名称/列名搜索；`/assets/:id` 展示列清单（类型/可空/描述/上下游数）、一跳血缘图、结构变更时间线，并支持"登记变更"补列后重解析。
- **SQL 转换与解析**：`/transformations` 左侧 SQL 编辑（行号 + 出错行高亮），右侧解析面板显示输入/输出资产、列映射表、`parse_status`、`parse_error` 原文（含 sqlglot 的 `line`/`col`）、`partial` 未展开列与可操作建议。
- **列级血缘图**：`/lineage` 选起点资产、方向（upstream/downstream/both）、深度 1–4、粒度（资产级/列级）；节点按 `AssetType` 分形状，边按 `EdgeKind`（`aggregate` 粗线、`derived` 虚线、`join_key` 点线）与 `ParseStatus`（partial 半透明）分线型，环边橙红虚线。
- **影响分析与迁移清单**：`/impact` 选资产 +（可选）列 + 变更类型发起分析，报告分区（严重度汇总条 / 受影响资产与列 / 传播路径 / 环截断说明 / 迁移清单），清单可勾选并复制建议 SQL，历史报告可回看。
- **结构变更时间线**：编辑列清单时自动生成 `SchemaChangeEvent`（`source=manual`）。
- **审计日志**：写请求统一落 `audit_logs`（SQL 只存 `sha256` 与长度，不落原文）。
- **解析配额与限流**：SQL 字节数、单用户并发解析数、8s 解析超时；超限返回 429 + `E_PARSE_QUOTA` / 504 + `E_PARSE_TIMEOUT`。

---

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | React 18 + TypeScript 5 + Vite 5 + Zustand 5 + Tailwind CSS 3（CSS 变量 token）+ 自绘 SVG 血缘图 |
| 后端 | Python 3.11 + FastAPI 0.115 + SQLAlchemy 2.0 + Alembic + Pydantic v2 + JWT（python-jose）+ passlib[bcrypt] |
| 解析 | `sqlglot==26.33.0`（真实解析，非正则） |
| 异步 | Celery 5 + Redis 7（`lineage` / `impact` 队列） |
| 数据库 | PostgreSQL 16（本机已缓存 `postgres:16-alpine`，题目写 15，16 完全兼容） |
| 部署 | Docker Compose（5 服务）+ Nginx 反代 `/api` |

> 说明：题目指定 CodeMirror 6 / TanStack Query / `@xyflow/react`。为了减少镜像构建与离线依赖风险，本项目用**羊皮纸色 textarea + 行号高亮**替代 CodeMirror、用 **Zustand + fetch 封装**替代 TanStack Query、用**自绘 SVG 分层布局**替代 `@xyflow/react`。功能（编辑、出错行高亮、图探索、环边虚线、检查器）均保留，差异见 `test-artifacts/gb-546/TESTING.md`。

---

## 目录结构

```
gb-546/
├── docker-compose.yml          # 5 服务：frontend / backend / worker / db / redis
├── .env / .env.example
├── backend/
│   ├── Dockerfile              # 构建上下文为仓库根目录（同时把 worker/ 打进镜像）
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── app/
│   │   ├── main.py             # 入口：lifespan 建表 + seed，注册中间件与路由
│   │   ├── config/             # settings / database / redis / storage / logging
│   │   ├── models/             # 8 张表：users / data_assets / transformations / lineage_edges /
│   │   │                       #        impact_analyses / schema_change_events / audit_logs / quotas
│   │   ├── schemas/            # pydantic v2（common/user/data_asset/transformation/lineage/impact/quota/audit）
│   │   ├── routes/             # auth / assets / transformations / lineage / impact / quota / audit / health
│   │   ├── controllers/        # 只做装配与响应包装（按实体分文件）
│   │   ├── services/           # asset / transformation / parse / lineage / impact / cycle / quota / audit /
│   │   │                       # permission / schema_change
│   │   ├── middlewares/        # auth / rbac / audit_logger / parse_guard / error_handler
│   │   ├── parsers/            # context / scope / projection / star / graph / engine（列级解析引擎）
│   │   ├── utils/              # jwt / password / logger / formatters / pagination / hashing / errors
│   │   ├── constants/          # asset / lineage / parse / impact / change / edge / roles / error_codes /
│   │   │                       # log_templates（38 条模板）/ messages / limits
│   │   ├── alembic/            # env.py + versions/0001_initial.py
│   │   └── scripts/            # seed_demo.py（幂等）/ wait_for_db.py
│   └── scripts/                # 容器内可执行：python -m scripts.seed_demo
├── worker/                     # 独立容器（复用 backend 镜像，PYTHONPATH=/app/backend:/app）
│   ├── celery_app.py           # 队列 lineage/impact、soft/hard time limit、重试
│   ├── tasks/                  # parse_tasks.py / impact_tasks.py
│   └── parsers/                # context/scope/projection/star/graph：复用 app.parsers 的同一实现
└── frontend/
    ├── Dockerfile              # node:20-alpine 构建 → nginx:1.27-alpine 托管
    ├── nginx.conf              # /api/ 反代 backend:8000，SPA fallback，client_max_body_size 8m
    └── src/
        ├── api/                # client/auth/assets/transformations/lineage/impact/quota/audit
        ├── stores/             # auth/asset/transformation/lineage/impact/quota/audit（zustand）
        ├── types/              # user/dataAsset/transformation/lineageEdge/impact/parse/audit/quota
        ├── components/common/  # LineageGraph/ColumnTag/AssetBadge/SqlEditor/ImpactTable/EmptyState/
        │                       # SeverityMeter/CycleWarning/RequireRole/ErrorPanel
        ├── components/layout/  # AppShell/RailNav/AssetInspector
        ├── hooks/              # useLineageLayout/useParseResult/useAuth/useQuota
        ├── pages/              # Assets/AssetDetail/Transformations/Lineage/Impact/Login
        ├── router/             # guards.tsx（路由守卫）
        ├── utils/              # graphLayout/sqlSnippet/request/formatCount
        ├── constants/          # 7 组枚举 + roles/errorCodes/messages
        └── styles/             # tokens.css（oklch 深墨蓝/黄铜/羊皮纸）+ global.css
```

`worker/parsers/` 每个文件职责一句话：`context.py` 解析上下文（输入资产列清单、方言、告警与 partial 收集）；`scope.py` 作用域栈（CTE / 子查询 / 派生表注册与查找）；`projection.py` 投影表达式 → 列级边（聚合/派生分类）；`star.py` `SELECT *` 展开与 partial 判定；`graph.py` 有向图构建、Tarjan 环检测、可达性 BFS。它们统一 `from app.parsers.X import *`，保证 backend 同步解析与 worker 异步解析走**同一份**实现。

---

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `COMPOSE_PROJECT_NAME` | `datatrace` | 容器名前缀 |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` | `datatrace_db` / `datatrace_user` / `datatrace_pwd` | PostgreSQL 库与账号 |
| `DB_PORT` | `17615` | db 端口映射 |
| `FRONTEND_PORT` / `BACKEND_PORT` | `18115` / `19115` | 前端 / 后端端口映射 |
| `REDIS_URL` | `redis://redis:6379/0` | Celery broker + 解析结果短期缓存 |
| `JWT_SECRET` | `change_me_to_a_long_random_string` | JWT 签名密钥（生产必须改） |
| `ARTIFACT_DIR` | `/data/artifacts` | 共享卷：原始 SQL 与解析快照 JSON |
| `MAX_SQL_BYTES` | `204800` | 单段 SQL 上限 |
| `PARSE_TIMEOUT_MS` | `8000` | 解析超时 |
| `SEED_DEMO` | `true` | backend 启动时自动 seed |

---

## Docker 部署说明

- **端口映射**：`18115:80`（frontend）、`19115:8000`（backend）、`17615:5432`（db）。Redis 不映射宿主机。
- **命名卷**：`db_data`（PostgreSQL 数据）、`redis_data`（AOF）、`artifact_data`（SQL 原文 + 解析快照 JSON）。
- **健康检查**：db `pg_isready`、redis `redis-cli ping`、backend `curl -f /api/health`、worker `celery inspect ping`、frontend `wget --spider`。
- **构建上下文**：因为 worker 需要把根目录 `worker/` 打进镜像，`backend` 与 `worker` 的 build context 都是仓库根目录（`dockerfile: backend/Dockerfile`），而不是 `./backend`。这是相对题目示例唯一的结构性调整，README 与 `TESTING.md` 均已注明。
- **常见问题**：
  - 首次启动 `backend` 需要等 db healthy 后建表，约 20~40 秒；
  - `parse_status` 一直 `pending` 说明 worker 没起来或 `enqueue-parse` 未被消费，`docker compose logs worker` 查看；
  - `SELECT *` 无法展开时：到 `/assets/:id` 用「登记变更」补全上游列清单，再回 `/transformations` 点「保存并重新解析」；
  - 中文目录名下可正常运行：compose 文件只使用相对路径与命名卷，不依赖宿主机绝对路径。

---

## 解析能力矩阵（全部由 `sqlglot` 真实解析）

| 情形 | 例子 | `parse_status` | 边与 `edge_kind` |
|---|---|---|---|
| 基础投影 | `SELECT o.amount AS pay_amount` | `parsed` | `source → target`，`direct` |
| WITH CTE | 2 层 `WITH base AS (...), per_region AS (...)` | `parsed` | 递归溯源到真实资产，透传内层 `edge_kind` |
| 子查询 / 派生表 | `FROM (SELECT ... FROM x) g` | `parsed` | 别名 → 列集合，递归溯源 |
| 多输入 JOIN | `JOIN ... ON d.id = o.id` | `parsed` | 投影列正常出边；ON 中同源同列升级为 `join_key` |
| `SELECT *` 可展开 | 来源资产 `columns_json` 完整 | `parsed` | 逐列 `direct` |
| `SELECT *` 不可展开 | 来源资产 `columns_json` 缺列/为空 | **`partial`** | 只展开已登记列，`report_json.unresolved` 记 `["*"]` + 来源资产 + 缺失列 |
| 聚合 | `SUM/COUNT/AVG/MAX/MIN(...)` | `parsed` | `aggregate` |
| 表达式 | `CAST / CONCAT / CASE / 算术` | `parsed` | `derived`，`expression_text` 存原始片段（≤512 字符） |
| 无法解析 | `SELECT * FORM x` | **`failed`** | 无边；`parse_error` 保留 sqlglot 原文 + `line/col` |
| 裸列多候选 | JOIN 两侧同名列 | `partial` | 取最内层作用域并记 warning |

> 说明：`UNION` / `EXCEPT` / `INTERSECT` 暂未做列级展开，会显式标 `partial` 而不是假装解析成功。
> 同一条 `(transformation, source_column, target_column)` 只保留一条边（数据库唯一约束），因此 `join_key` 作为更具体的类型**替代**同对的 `direct`，不新增第二条边。

---

## 影响分析规则

**严重度定级（`services/impact_service.py` 的显式规则表）**

| 规则 | 结果 |
|---|---|
| 最小传播深度 `depth == 1` | `high` |
| `depth == 2..3` | `medium` |
| `depth >= 4` | `low` |
| 命中 `materialized_view` | 升一级 |
| 命中环 | `critical` |
| `change_type == drop_column` | 升一级（上限 `critical`） |

- **遍历方向**：从 `(target_asset_id, target_column)` 沿 `source → target` 正向 BFS 求下游可达集合（即 `target → 下游`），`depth` 上限 12；超出置 `truncated: true` 并在报告里明确告知。
- **`affected_count`** = 去重后的 `(asset_id, column)` 对数；`cte_result` 类资产**计入** `affected_count`，但**不进迁移清单**。
- **报表数** = 受影响资产中排除 `cte_result` 的资产数（演示数据为 2）。
- **环处理**：Tarjan 求强连通分量识别环；有环不影响保存，写入 `report_json.cycles`（`nodes` + `sample_path`），环边在图中虚线标记；命中环时报告严重度升为 `critical`。
- **缓存**：同 `(target_asset_id, target_column, change_type)` 重复发起直接命中历史快照（`cached: true`），不重算；`force=true` 可强制重算。

**迁移清单 `action` 四种取值**

| action | 触发条件 | 含义 |
|---|---|---|
| `rewrite_sql` | 下游直接引用该列（`direct` / `join_key`），或 `rename_column` | 重写下游 SELECT 表达式 |
| `add_cast` | 下游在该列上做聚合/表达式计算（`aggregate` / `derived`），且 `change_type=change_type` | 在聚合/表达式前显式 `CAST` |
| `drop_downstream` | `change_type=drop_column` 且下游是普通表/视图 | 先移除下游引用再删列 |
| `refresh_mv` | 命中物化视图 | 刷新/重建物化视图 |

每条清单项包含 `{asset_id, asset_name, column, action, suggested_sql, reason}`。

---

## 枚举出现位置清单

### AssetType（`table` / `view` / `materialized_view` / `cte_result`）
- 后端：`constants/asset.py`（定义 + 中文名 + `REPORT_EXCLUDED_ASSET_TYPES`）、`models/data_asset.py`、`schemas/data_asset.py`（Literal）、`services/asset_service.py`、`services/impact_service.py`（物化视图升级 / cte_result 排除）、`services/lineage_service.py`（节点形状数据）、`parsers/context.py`、`utils/formatters.py`、`constants/log_templates.py`
- 前端：`constants/assetType.ts`（`as const` + 联合类型 + 形状映射）、`types/dataAsset.ts`、`components/common/AssetBadge.tsx`、`components/common/LineageGraph.tsx`（节点形状）、`pages/Assets.tsx`（筛选）、`pages/Transformations.tsx`

### LineageDirection（`upstream` / `downstream` / `both`）
- 后端：`constants/lineage.py`、`schemas/lineage.py`（Literal）、`services/lineage_service.py`（遍历方向）、`routes/lineage.py`（query 参数）、`utils/formatters.py`
- 前端：`constants/lineageDirection.ts`、`pages/Lineage.tsx`（方向切换器）、`api/lineage.ts`、`stores/lineageStore.ts`、`utils/graphLayout.ts`（布局朝向）

### ParseStatus（`pending` / `parsed` / `partial` / `failed`）
- 后端：`constants/parse.py`、`models/transformation.py`、`schemas/transformation.py`、`services/parse_service.py`（判定与回写）、`worker/tasks/parse_tasks.py`、`constants/error_codes.py`、`constants/log_templates.py`（`PARSE_PARTIAL_STAR` / `PARSE_FAILED_WITH_POS`）、`utils/formatters.py`
- 前端：`constants/parseStatus.ts`、`types/transformation.ts`、`types/parse.ts`、`hooks/useParseResult.ts`（状态机）、`components/common/SqlEditor.tsx`（状态条 / 出错行）、`pages/Transformations.tsx`

### ImpactSeverity（`low` / `medium` / `high` / `critical`）
- 后端：`constants/impact.py`（含 `DEPTH_SEVERITY_RULES`）、`models/impact_analysis.py`、`schemas/impact.py`、`services/impact_service.py`（定级）、`utils/formatters.py`、`constants/log_templates.py`（`IMPACT_GRADED`）
- 前端：`constants/impactSeverity.ts`、`types/impact.ts`、`components/common/SeverityMeter.tsx`、`components/common/ImpactTable.tsx`（排序 / 配色）、`pages/Impact.tsx`（汇总条）

### ChangeType（`add_column` / `drop_column` / `rename_column` / `change_type`）
- 后端：`constants/change.py`、`models/impact_analysis.py`、`models/schema_change_event.py`、`schemas/impact.py`、`services/impact_service.py`（迁移建议分支）、`services/schema_change_service.py`、`constants/log_templates.py`
- 前端：`constants/changeType.ts`、`types/impact.ts`、`pages/Impact.tsx`（表单）、`pages/AssetDetail.tsx`（时间线）、`components/common/ImpactTable.tsx`、`utils/sqlSnippet.ts`

### EdgeKind（`direct` / `derived` / `aggregate` / `join_key`）
- 后端：`constants/edge.py`（含 `EDGE_KIND_PRIORITY`）、`models/lineage_edge.py`、`parsers/projection.py`（赋值）、`parsers/engine.py`（join_key 细化）、`services/parse_service.py`（去重优先级）、`services/lineage_service.py`、`utils/formatters.py`
- 前端：`constants/edgeKind.ts`、`types/lineageEdge.ts`、`components/common/LineageGraph.tsx`（边样式）、`components/common/ImpactTable.tsx`、`utils/graphLayout.ts`（环边分离）、`pages/Transformations.tsx`（列映射）

### AssetStatus（`active` / `deprecated` / `draft`）
- 后端：`constants/asset.py`、`models/data_asset.py`、`schemas/data_asset.py`、`services/asset_service.py`（筛选）、`services/impact_service.py`（只对 active 下游计入迁移清单）、`constants/log_templates.py`
- 前端：`constants/assetStatus.ts`、`types/dataAsset.ts`、`components/common/AssetBadge.tsx`（角标）、`pages/Assets.tsx`（筛选）

---

## 本地开发（不使用 Docker）

```bash
# 先起 PostgreSQL 与 Redis（可用 docker compose up -d db redis）
cd backend
pip install -r requirements.txt
export DB_HOST=localhost DB_PORT=17615 DB_NAME=datatrace_db DB_USER=datatrace_user DB_PASSWORD=datatrace_pwd
export REDIS_URL=redis://localhost:6379/0 PYTHONPATH=$PWD
python -m scripts.wait_for_db
uvicorn app.main:app --reload --port 19115

# worker（另开终端）
cd .. && PYTHONPATH="$PWD/backend:$PWD" celery -A worker.celery_app.celery_app worker -Q lineage,impact -l info

# 前端
cd frontend
npm config set registry https://registry.npmjs.org
npm install
npm run dev   # http://localhost:5173（/api 已代理到 19115）
```

> 主机 npm 默认 registry 指向不可达镜像源，安装依赖必须显式 `--registry=https://registry.npmjs.org`。

---

## License

MIT
