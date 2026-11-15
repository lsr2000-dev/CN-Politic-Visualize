# 性能优化

## 1. 目标与负载假设

| 指标 | 目标 |
| --- | --- |
| 快照接口（Redis 命中） | p95 < 50ms |
| 快照接口（回源 PostgreSQL） | p95 < 300ms |
| 首屏可交互（4G） | < 2.5s |
| 时间轴拖拽 | 55–60fps，无长任务 > 50ms |
| 连续拖动请求数 | ≤ 3 次/秒/用户 |
| 单日快照体积 | ~120KB JSON，gzip 后 ~25KB |

规模假设：31 省 × 4 套班子 ≈ 120 条在任记录；全量 348 段任职。地市扩展后
约 330 × 4 ≈ 1,300 条，仍在单机 PostgreSQL  comfortable 范围。

## 2. 前端：把“每帧”与“每次请求”解耦

### 2.1 拖拽链路

```
pointermove (60–120Hz)
  → timeline.setDate()            纯内存，~0.05ms
  → CSS transform / left 更新     合成层，不触发布局
  → debounce 180ms / maxWait 420ms
  → map.loadSnapshot()            每 420ms 最多一次
  → AbortController.abort()       取消上一请求
  → ETag → 304 或 120KB JSON
  → chart.setOption({series:[{data}]})  只更新数据
```

`useSnapshotSync`：

```ts
const fetchSnapshot = useDebounceFn(
  (date: string) => map.loadSnapshot(date),
  180,
  { maxWait: 420 },
);
watch(() => timeline.currentDate, (date) => fetchSnapshot(date));
```

- **为什么不是 throttle**：throttle 会在拖动全程固定频率发请求；debounce + maxWait
  在停下时立即给最终结果，同时保证长拖动期间不会超过 420ms 不刷新。
- **为什么不用 `watch(..., { deep: true })`**：`currentDate` 是字符串，浅监听即可；
  deep 会遍历 snapshot 大对象。
- **为什么地图不直接监听日期**：地图只监听 `map.snapshot`，避免每帧 `setOption`。

### 2.2 请求层

- **AbortController**：每次请求前 abort 上一个；`requestSeq` 丢弃乱序响应，防止
  “旧日期覆盖新日期”。
- **ETag 缓存**：按日期保存 `{data, etag}`，最多 48 个（约 5–6MB）。重复访问同一
  日期返回 304，不重新传输。
- **LRU 上限**：超过 48 个删除最旧，避免长时间会话内存膨胀。
- **错误不打断交互**：保留旧 snapshot，顶部显示细进度条；错误卡片可重试。

### 2.3 ECharts

- 按需引入：`MapChart + TooltipComponent + CanvasRenderer`，未引入完整 `echarts`。
- 首次 `setOption` 全量；后续只更新 `series[0].data` 与 `markPoint`。
- `animationDurationUpdate: 420`、`animationEasingUpdate: "cubicOut"`，避免 31 省同时
  剧烈过渡。
- `roam: true` 的缩放/平移由 ECharts 内部处理，不触发 Vue 更新。
- 容器尺寸变化用 `ResizeObserver` + 80ms 防抖，避免窗口拖动时连续 `resize()`。
- 31 省 Labels 用 9px 并自动重叠隐藏；后续可切换 `label.show=false` 只保留 tooltip。

### 2.4 渲染与内存

- `shallowRef` 保存 ECharts 实例与 GeoJSON，避免 Vue 深度代理大对象。
- 列表最多几十行，无需虚拟滚动；若扩展地市（3000+ 行），使用 `vue-virtual-scroller`。
- 面板切换用 `v-show`（四套班子折叠）保留 DOM；重内容（全屏席位条带）用 `v-if`
  延迟请求。
- 时间轴事件标记只有 6 个，纯 CSS 定位。
- 所有动画尊重 `prefers-reduced-motion`。

### 2.5 首屏

- GeoJSON 582KB：`public/geo/china-provinces.json`，Nginx `Cache-Control: immutable`，
  二次访问直接命中磁盘缓存。
- ECharts chunk 433KB（gzip 146KB）独立分包，不阻塞 Vue 主包。
- 启动顺序：`meta` 与 GeoJSON 并行 → 首张快照 → 渲染；Boot 遮罩显示进度。
- 后续可把 GeoJSON 简化为 TopoJSON（约 1/3 体积），或按需加载地市边界。

## 3. 后端：两级缓存与缓存键设计

### 3.1 分层

```
请求 → MemoryLRU（进程内，60s）
     → Redis（共享，900s + 抖动）
     → PostgreSQL（GiST 时点查询）
```

- 进程 LRU 吸收同一实例的瞬时重复（同一用户拖动回退）。
- Redis 吸收跨实例重复；故障时自动降级，不阻塞请求。
- `CacheLayer` 对 Redis 异常设置 30s 熔断，避免每次请求都等超时。

### 3.2 Key 设计

统一前缀包含**数据集版本**，发布新数据即自然失效：

| Key | 示例 | TTL | 说明 |
| --- | --- | --- | --- |
| `polvis:{dataset}:meta:v3` | `polvis:2026.10:meta:v3` | 24h | 元信息 |
| `polvis:{dataset}:snap:{date}:{scope}` | `...:snap:2017-10-25:a1b2c3d4e5f6` | 900s + 0–120s 抖动 | 时点快照；scope 是 regions+categories 的 SHA-1 前 12 位 |
| `polvis:{dataset}:region-timeline:{code}:{scope}` | `...:region-timeline:310000:9f8e7d6c5b4a` | 1800s | 省级席位更替（scope 含起止日期） |
| `polvis:{dataset}:seat:{code}:{scope}` | `...:seat:110000:1a2b3c4d5e6f` | 1800s | 单席位历史（scope 含 seat_key + as_of） |
| `polvis:{dataset}:career:{id}:{scope}` | `...:career:64:6f5e4d3c2b1a` | 3600s | 个人履历（scope 含起止日期） |
| `lock:{key}` | `lock:polvis:...:snap:...` | 10s | 可选：防击穿 |

- **scope 用 hash 而非拼接全量代码**：31 个代码拼进 key 会超过可读性；hash 冲突概率
  可忽略（SHA-1 12 hex）。
- **日期不量化**：业务要求精确到日；4,700 个日期全部可缓存，热门日期自然集中。
- **TTL 抖动**：按 key 末 2 字节取模 120s，避免同一批 key 同时过期。

### 3.3 防击穿 / 防穿透

- **击穿**（热点 key 过期瞬间大量回源）：Redis `SET lock:{key} NX EX 10`，拿不到锁的
  请求 sleep 30–50ms 后重试读缓存；或进程内 singleflight（`asyncio.Future` map）。
  当前实现依赖 TTL 抖动 + 进程 LRU，生产高并发建议补 singleflight。
- **穿透**（查询不存在的省/席位）：Service 对 404 不缓存；可在网关对非法 6 位代码
  直接 422，避免落到 DB。
- **雪崩**（Redis 整体挂）：快速失败 + 回源限流；`CacheLayer` 已熔断 30s。
- **大 key**：快照 120KB，可接受；不要用 Hash 存单条 span。

### 3.4 HTTP 缓存

- `ETag`：响应体 SHA-1 前 20 位；`If-None-Match` 命中返回 304，节省带宽。
- `Cache-Control: public, max-age=60, stale-while-revalidate=300`：浏览器/CDN 可短期
  复用，SSR 场景也可用。
- Nginx 对 `/assets/*` 一年 immutable，`/geo/*` 一周。
- gzip 对 JSON 压缩比约 4–5 倍；生产可开 brotli。

## 4. 数据库

### 4.1 时点查询

```sql
SELECT ...
FROM polvis.v_tenure_expanded
WHERE period @> DATE '2017-10-25';
```

- `period` 是生成列 + GiST 索引，31 省数据下走 Bitmap Index Scan，实际 < 5ms。
- 不要写 `start_date <= d AND (end_date IS NULL OR end_date >= d)`：优化器难以稳定
  使用 GiST，且容易漏掉同日交接。
- `ORDER BY region_code, category, seat_rank` 的数据量小，排序开销可忽略。

### 4.2 热点日期物化

党代会/两会/省级换届日期的访问占比通常 > 60%。可增加：

```sql
CREATE TABLE polvis.province_snapshots (
  as_of date NOT NULL,
  region_code varchar(12) NOT NULL,
  payload jsonb NOT NULL,
  PRIMARY KEY (as_of, region_code)
);
```

发布数据版本时，对 2012-11-08、2013-03、2017-10、2018-03、2022-10、2023-03 等
日期预计算；API 先查该表，未命中再走实时查询。注意 payload 需带版本号，避免旧数据。

### 4.3 其他

- 连接池：SQLAlchemy `pool_size=8, max_overflow=4, pool_pre_ping=True`。
- 只读副本：快照查询走 replica，写入/导入走 primary。
- `ANALYZE` 在批量导入后执行；`pg_stat_statements` 监控慢查询。
- 地市扩展后按 `start_date` 分区，或把 `tenures` 拆为 `tenures_province` /
  `tenures_prefecture`。

## 5. 缓存失效

1. 导入完成 → 写入 `dataset_versions`（新 id）→ 更新 `polvis:dataset:current`。
2. API 启动时读取当前 dataset id；所有 key 自动带新前缀，旧 key 自然过期。
3. 如需立即清理：`SCAN 0 MATCH polvis:old:* COUNT 500` 分批 `UNLINK`，禁止 `KEYS *`。
4. 单条修订（管理端）：删除对应 `seat/career/snap` key；或直接 bump 版本，简单可靠。

## 6. 度量与压测

```bash
# 后端
k6 run scripts/load-test.js          # 目标：500 VU，snapshot p95 < 300ms
autocannon -c 50 -d 30 "http://127.0.0.1:8000/api/v1/map/snapshot?date=2017-10-25"

# 前端
pnpm build && pnpm preview
# Chrome DevTools → Performance → 拖动时间轴 10s，检查 Long Tasks / Layout Shift
```

关键指标：

- `X-Cache` HIT 比例（目标 > 85%）。
- Redis 内存 / 命中率 / 平均 RTT。
- PG `EXPLAIN (ANALYZE, BUFFERS)` 是否走 `tenures_period_gix`。
- 浏览器 `PerformanceObserver` 记录 `longtask` 与 `event` 延迟。
