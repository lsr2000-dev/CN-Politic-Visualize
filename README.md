# 地方政治人事 · 时空图谱

> 十八大以来中国地方政治人事时空可视化系统  
> A spatiotemporal archive of China's provincial leadership, 2012 – present.

在地图与时间轴上双重检索 31 个省级行政区「四套班子」主官，穿透到个人跨省、跨部门履历，并提供与数据库同源的官员名册表格。
项目包含可运行的 Vue 3 前端、FastAPI 读取层、PostgreSQL/PostGIS 时态数据模型与 Docker 部署。

![总览](docs/assets/overview.png)

## 功能

- **地图 × 时间轴双向联动**：拖动时间轴实时刷新 31 省班子切片；点击省份下探右侧详情。时间轴采用 180ms debounce + 420ms maxWait、`AbortController` 取消过期请求、`requestAnimationFrame` 平滑补间，避免高频重绘与请求风暴。
- **四套班子结构**：党委（书记/副书记）、人大（常委会主任）、政府（省长/市长/自治区主席）、政协（主席），按届次与任职先后排序，代理（代省长/代市长）、现任名册快照与行政级别单独标记。行政级别按任职时点认定：中央政治局委员为副国级，政治局常委为正国级；同一人进入政治局前仍按正省部级显示。
- **三种详情形态**：侧边栏 Sidebar、可拖拽浮动窗 Floating、全屏沉浸 Fullscreen；一键钉住最多 6 个省进入并置对比。
- **条目化穿透**：点击官员打开个人档案与十八大以来履历甘特图（跨省/中央机构分轨、代理斜纹、任职时长、重叠任职分层）；档案显示**任职前 / 离任后**岗位、行政级别，以及退休、接受审查、开除党籍、病逝等状态事件；点击「历任」查看该席位自 2012 年以来的正式与代理任职序列、空档天数与离任原因。
- **全国官员名册**：与数据库同源的分页表格，支持姓名/籍贯、省份、班子、状态、级别筛选，CSV 导出，行点击穿透到个人档案；顶部展示数据版本、截止日与覆盖率。
- **数据覆盖报告**：`/coverage` 与名册页“覆盖看板”给出 31 省 × 4 正职的当前/历史完整率、确认空缺与来源缺口，区分“未收录”与“真实空缺”。
- **省级席位更替**：全屏模式下展示该省四套班子所有席位在 2012–2026 的完整更替条带。
- **检索与深链**：`/` 唤起官员检索（姓名/籍贯）；`?date=2017-10-25&region=332000&view=fullscreen`、`?directory=1` 可直接分享任意时空切片或名册视图。
- **数据可信度提示**：每条记录带 `verified` 标记，页面常驻数据覆盖截止日；查询超出覆盖范围时标注「待更新」，不伪造当前状态。

### 界面

| 全国官员名册 / 覆盖看板 | 官员履历 + 前/后岗位 |
| --- | --- |
| ![名册](docs/assets/directory.png) | ![履历](docs/assets/officer-career.png) |

| 全屏沉浸 + 席位更替 | 跨省对比 |
| --- | --- |
| ![全屏](docs/assets/fullscreen.png) | ![对比](docs/assets/compare.png) |

## 架构

```mermaid
flowchart LR
  subgraph Browser["浏览器"]
    UI["Vue 3 + TS<br/>Pinia / Tailwind"]
    Map["ECharts Map<br/>GeoJSON 31 省"]
    TL["Timeline<br/>rAF + debounce"]
  end
  NG["Nginx<br/>静态资源 + /api 反代"]
  API["FastAPI<br/>Pydantic v2"]
  R[("Redis<br/>时点快照 / ETag")]
  PG[("PostgreSQL 16<br/>PostGIS 3.4<br/>daterange + GiST")]
  GEO["DataV GeoJSON"]

  UI --> Map
  UI --> TL
  UI -->|"GET /api/v1/map/snapshot"| NG
  NG --> API
  API -->|"cache hit"| R
  API -->|"cache miss"| PG
  Map -.->|"registerMap"| GEO
```

- **时态模型**：`tenures` 一条记录 = 一人一岗一段连续任职，使用生成列 `period daterange` 表达半开区间；所有「某日谁在任」都归结为 `period @> date`，命中 GiST 索引。
- **代理与兼任是独立维度**：`is_acting` / `is_concurrent` 不污染正式任职的唯一性约束；同一席位正式任职通过 `EXCLUDE USING gist` 保证不重叠。
- **读多写少**：读路径 Redis + 进程 LRU 两级缓存，ETag/304；写路径（导入/修订）通过 `change_log` 审计。

## 快速开始

### 方式一：Docker 全栈（推荐）

```bash
cp .env.example .env          # 修改 POSTGRES_PASSWORD
docker compose up --build
```

- Web：<http://localhost:8080>
- API 文档：<http://localhost:8000/docs>
- PostGIS：`localhost:5432/polvis`

首次启动会自动执行 `infra/initdb/01_schema.sql`、`02_seed.sql`、`03_geometry.sql`，建表、导入 640 条演示任职、25 条状态事件和 31 省边界。

> 本次为 schema v2（新增行政级别、多成员岗位、`officer_events`、名册视图）。若已有旧版本地数据库，请先 `docker compose down -v` 再启动，或手工执行迁移；生产库请勿直接删除 volume。

### 方式二：本地开发（零数据库）

后端默认 `POLVIS_DATA_MODE=json`，直接读取仓库内置的策展数据集，无需 PostgreSQL/Redis：

```bash
# backend
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend
uvicorn app.main:app --reload --port 8000

# frontend（另开终端）
cd frontend
pnpm install
pnpm dev
```

打开 <http://127.0.0.1:5173>。Vite 将 `/api` 代理到 `127.0.0.1:8000`。

### 方式三：PostgreSQL 模式（本地）

```bash
docker compose up -d postgres redis
cd backend
set POLVIS_DATA_MODE=postgres
set POLVIS_DATABASE_URL=postgresql+psycopg://polvis:polvis@127.0.0.1:5432/polvis
uvicorn app.main:app --reload --port 8000
```

## 测试与构建

```bash
cd backend && pytest -q                    # 19 项 API 契约测试
cd frontend && pnpm typecheck && pnpm build
```

## API 一览

| Method | Path | 说明 |
| --- | --- | --- |
| GET | `/api/v1/meta` | 数据集、分类、指标、时间轴里程碑、GeoJSON 地址 |
| GET | `/api/v1/map/snapshot?date=2017-10-25` | 31 省四套班子时点快照（地图主数据源） |
| GET | `/api/v1/regions/{code}/leaders?date=` | 单省详情 |
| GET | `/api/v1/regions/{code}/timeline` | 该省全部席位更替条带 |
| GET | `/api/v1/regions/{code}/seats/{seat_key}/history` | 单个席位历任（含代理、空档） |
| GET | `/api/v1/officers?q=李强` | 官员检索 |
| GET | `/api/v1/officers/{id}?date=` | 档案 + 当前职务 |
| GET | `/api/v1/officers/{id}/career?from=&to=` | 履历甘特图数据（分轨 + 前后岗位 + 状态事件） |
| GET | `/api/v1/directory?region=332000&status=active` | 官员名册表格数据（筛选/分页/CSV） |
| GET | `/api/v1/coverage` | 当前与历史时点数据覆盖率、确认空缺 |
| GET | `/api/v1/compare?regions=110000,332000&date=` | 多省并置（≤6） |
| GET | `/api/v1/health` | 仓储与缓存状态 |

完整契约、错误码与缓存头见 [docs/api.md](docs/api.md)。

## 数据说明（务必阅读）

仓库内置数据是**产品演示样例**，不是权威人事档案：

- 覆盖 `2012-11-08` 至 `2026-10-29`（二十届五中全会闭幕日），月份级精度，部分日期依据公开报道推定；
- 现任岗位的起始月份按公开任免公告/换届届次推定，页面以“约 X 年/月”显示迄今任职时间，不再一律显示“—”；精确到日仍需逐人补任免公告。
- 当前时点：四套班子正职 **31/31 省份连续覆盖**；其中 9 席正职空缺由第一副职/党组书记主持工作，页面标注“主持工作”，不伪造正式正职；
- **历史时点**：2017/2022 检查点四套齐全省份为 31/31；2012 年 11 月（2013 换届前）仍为 3/31；完整率报告见 [docs/data-coverage.md](docs/data-coverage.md)，这是下一阶段的主要数据工作；
- 全部记录 `verified=false`，页面标注数据截止日，超出范围显示「待更新」；
- 官员履历字段仅对部分重点人物收录，未收录显示「待补充」，**不做臆测填充**；
- 生产使用前须接入可审计来源（新华社/人民日报/地方政府官网/人大公告），逐条复核并在 `sources` 表留痕。

详见 [docs/data-governance.md](docs/data-governance.md) 与 [docs/data-coverage.md](docs/data-coverage.md)。

## 目录结构

```
.
├─ backend/                 FastAPI + Pydantic v2 + SQLAlchemy/psycopg
│  ├─ app/                  api / services / repositories / domain
│  ├─ app/data/dataset.json 内置演示快照（由 scripts/build_seed.py 生成）
│  └─ tests/                API 契约测试
├─ frontend/                Vue 3 + TS + Pinia + Tailwind + ECharts
│  ├─ src/components/       map / timeline / panel / charts / drawers
│  ├─ src/stores/           timeline / map / app / officer
│  ├─ src/composables/      snapshot sync / draggable / url state / shortcuts
│  └─ public/geo/           31 省 GeoJSON（DataV GeoAtlas）
├─ infra/initdb/            DDL + 种子 SQL + PostGIS 边界
├─ scripts/                 策展数据源、种子生成、GeoJSON → SQL
├─ docs/                    架构 / API / 数据库 / 路线图 / 性能 / 数据治理
└─ docker-compose.yml
```

## 文档

- [系统架构](docs/architecture.md)：读路径、状态同步、组件树、关键决策
- [数据库设计](docs/database.md)：ER、DDL 要点、时态约束、PostGIS、导入流水线
- [API 规范](docs/api.md)：请求/响应、错误码、缓存与 ETag
- [开发路线图](docs/roadmap.md)：冷启动 6 周计划、验收标准、风险
- [性能优化](docs/performance.md)：拖拽渲染、Redis Key、缓存击穿、DB 索引
- [数据治理](docs/data-governance.md)：来源分级、日期精度、复核流程
- [数据完整率报告](docs/data-coverage.md)：当前/历史覆盖率、9 席主持工作、下一步数据计划
- [数据查漏补缺报告](docs/data-audit.md)：官员基本信息、纪律结果、历史缺口审计
- [信息收集与交叉核对规则](docs/data-collection-rules.md)：来源分级、双源规则、山西 9 个月空档纠正
- [省级时间线审计清单](docs/timeline-audit.md)：31 省 × 4 正职逐省状态与下一步顺序
- [官员基础字段补全报告](docs/officer-bio-enrichment.md)：出生、籍贯、性别、民族、入党时间完整度与缺口
- [中央机构模块（第一批）](docs/central-module.md)：四套班子、两高、群团、军委、纪委监委、议事协调及中央委员徽标
- [历史交接空档与主持工作审计](docs/handover-audit.md)：35 处跨届空档、9 席主持工作的具体位置

## 技术栈

Vue 3.5 · TypeScript · Pinia · TailwindCSS 3.4 · ECharts 5.6 · VueUse · FastAPI · Pydantic v2 · PostgreSQL 16 · PostGIS 3.4 · Redis 7 · Docker Compose

## 免责声明

本项目仅用于技术研究与数据可视化演示，不构成对任何个人任职状态的权威认定。历史人事信息以官方发布为准。若数据权利人认为内容不妥，请联系删除。
