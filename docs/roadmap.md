# 开发路线图

> **2026-11 状态更新**：数据模型、API、三视图、席位/官员穿透、名册表格、覆盖看板已完成。
> 现任四套正职 22/31 完整、31/31 已说明（9 席公开确认空缺）；2012–2025 人大/政协正职
> 仍是主要数据缺口（2017/2022 检查点 4/31）。下一步按 P1→P3 补历史 B、副职 B、全量 C。
> 详见 [data-coverage.md](data-coverage.md)。

目标：用 6 周从零交付一个可演示、可扩展、数据可追溯的省级人事时空 MVP。以下按
“先事实、后交互、再扩展”的顺序排列，避免在数据未结构化时过早打磨地图。

## 0. 冷启动前置（第 1 周前半）

### 0.1 冻结领域模型

- 确定 31 个省级 `regions.code`（GB/T 2260）与 `level/parent_code`。
- 确定四套班子分类：`party / congress / government / cppcc`。
- 确定席位键：`party_secretary`、`governor`、`congress_chair`、`cppcc_chair`，
  副书记/副省长后续加 `party_deputy_secretary` 等。
- 确定时间语义：一条 `tenure` = 一人一岗一段连续任职；代理独立记录；兼任独立标记。
- 产出：`infra/initdb/01_schema.sql` + 本文档的字段字典。

### 0.2 建立来源与模板

- 来源分级：新华社/人民日报/中国经济网 > 省级政府官网/人大公告 > 地方媒体。
- 建立 CSV 模板（本项目 `data/seed` 的等价物）：
  `region_code, category, title, officer_name, start_month, end_month, is_acting, source_url, verified`
- 每个省至少完成党委书记、政府主官两条主线（2012-11 至 coverage_end）。
- 先不追求全量副书记/人大/政协，避免“广度拖死准确度”。

### 0.3 技术基线

- 仓库初始化：`backend`、`frontend`、`infra`、`scripts`、`docs`。
- CI：后端 `pytest` + `ruff`；前端 `vue-tsc --noEmit` + `vite build`。
- 约定 API 版本 `/api/v1`、错误结构、日期格式。

**验收**：31 省 × 2 主官 × 2012–2025 的时间线无重叠、无负区间；每条记录有来源。

## 1. 第 1 周：数据管道 + 时点查询

- 写导入脚本：CSV → 暂存表 → 校验 → `tenures`。
- 实现 `v_tenure_expanded` 与 `fn_snapshot(date)`。
- 实现 `GET /map/snapshot`（先不做缓存），用 `EXPLAIN ANALYZE` 确认走 GiST。
- 编写 10 条数据质量 SQL（重叠、空档、负区间、未复核）。
- 产出：能在 50ms 内返回 31 省 2017-10-25 快照的 API。

**验收**：`curl /map/snapshot?date=2017-10-25` 返回 31 个省、字段完整；`pytest` 覆盖
时点/代理/空档。

## 2. 第 2 周：前端壳 + 地图 + 时间轴

- Vue 3 + Vite + Tailwind + Pinia 初始化；设计 token（墨色/朱砂/米纸）。
- ECharts 注册 31 省 GeoJSON；实现指标着色、tooltip、点击高亮。
- 时间轴：年刻度 + 事件标记 + 拖拽；引入 `debounce(180, maxWait 420)` + rAF 补间。
- `useTimelineStore` / `useMapStore`；快照请求 AbortController + 日期缓存。
- 产出：地图与时间轴联动，拖动时地图按 ~400ms 节奏刷新。

**验收**：连续拖动 10 秒，网络面板请求数 < 30；地图无白屏；时间轴 55fps。

## 3. 第 3 周：四套班子面板 + 三视图

- `DetailPanel`：sidebar / floating / fullscreen 三形态；floating 支持指针拖拽与视口钳制。
- `RegionDetail`：四套班子手风琴、代理标记、任期进度条、空状态。
- 钉住 + `CompareTray` + `CompareOverlay`（≤6 省并置）。
- 移动端：侧栏变为全屏抽屉，视图切换折叠为单按钮循环。

**验收**：三种模式切换不丢状态；钉住 3 省可对比；390px 宽度无横向滚动。

## 4. 第 4 周：穿透（席位 / 官员 / 甘特）

- `/regions/{code}/seats/{seat_key}/history`：正式/代理序列、空档天数。
- `/officers/{id}/career`：按地区/中央机构分轨，重叠 span 分层。
- `CareerGantt`：年轴、代理斜纹、hover 详情、点击聚焦。
- `OfficerDrawer` / `SeatDrawer` 互斥与返回链路。
- 全屏增加 `ProvinceTimeline`（四套班子席位更替）。

**验收**：李强从浙江省长 → 江苏省委书记 → 上海市委书记 → 中央，4 条轨道正确；
点击任一 span 能回溯到该段任职。

## 5. 第 5 周：数据扩展 + 质量

- 补副书记、人大主任、政协主席；优先做 6–8 个重点省。
- 建立 `sources` / `tenure_sources`，每条记录至少一个来源。
- 人工复核 `verified=true`；未复核数据在 UI 标注。
- 对 2012-11、2017-10、2022-10、2023-03 四个关键日期做快照对账。

**验收**：重点省四套班子完整率 ≥ 90%；关键日期与公开报道一致；无未解释空档。

## 6. 第 6 周：性能、部署、演示

- Redis 缓存 + ETag/304；压测快照接口（k6/autocannon）。
- Docker Compose 全栈；Nginx gzip/缓存头；健康检查。
- 首屏优化：ECharts 按需引入、GeoJSON 预加载、骨架屏。
- 录制 3 分钟演示：时间轴 → 2017 上海 → 李强履历 → 对比北京/上海/广东 → 深链。
- 产出：部署文档、性能报告、已知问题清单。

**验收**：冷缓存 p95 < 300ms，热缓存 p95 < 50ms；Lighthouse Performance ≥ 85（桌面）。

## 7. 数据扩展路线（MVP 之后）

| 阶段 | 内容 | 关键工作 |
| --- | --- | --- |
| P7 | 31 省四套班子全量 | 补 2012–2025 所有正职与代理，来源逐条挂接 |
| P8 | 副书记/副省长/常委 | 扩展 `positions.parent_position_id`，班子排序 |
| P9 | 地级市 | 330+ 地市行政区划、市级四套班子、地图下钻 |
| P10 | 中央部委 | `region_code=NULL` 的中央岗位，跨部门轨迹 |
| P11 | 关系与研究 | 同事网络、任期统计、导出 CSV/Parquet |

## 8. 角色建议

- **数据编辑 1–2 人**：来源检索、CSV 录入、复核；决定项目上限。
- **后端 1 人**：DDL、导入、API、缓存、部署。
- **前端 1 人**：地图/时间轴/面板/甘特/响应式。
- **设计/研究 0.5 人**：信息层级、术语、可视化叙事。

## 9. 风险与对策

| 风险 | 影响 | 对策 |
| --- | --- | --- |
| 任职日期只有月份 | 边界日期误判 | 全库 `*_precision`；UI 显示“YYYY.MM”；关键节点人工补日 |
| 同名官员 | 履历串人 | slug 消歧 + 出生年/籍贯校验；导入时人工确认 |
| 代理/正式交接 | 时间线重叠 | 半开区间 + 排他约束 + 导入校验 |
| 数据版权/合规 | 下架风险 | 只用公开履历；来源留痕；免责声明；可快速替换数据集 |
| 范围蔓延 | 6 周无法交付 | 冻结 MVP 为“31 省正职 + 三视图 + 甘特”；地市放 P9 |
| 地图性能 | 拖拽卡顿 | 只更新 series data；按需 ECharts；请求 debounce |

## 10. 完成定义（Definition of Done）

- 任意日期（2012-11-08 至 coverage_end）可在 300ms 内看到 31 省班子。
- 任一在任官员可在 2 次点击内看到其十八大以来完整轨迹。
- 任一席位可看到正式/代理/空档的完整序列。
- 3 省并置对比可用，移动端可用。
- 所有数据带来源或明确标注“待复核”；页面有数据截止提示。
- `docker compose up` 一条命令可复现。
