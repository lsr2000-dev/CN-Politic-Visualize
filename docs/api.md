# API 规范

Base URL：`http://127.0.0.1:8000/api/v1`（Docker 中由 Nginx 反代到同源 `/api/v1`）  
交互式文档：`/docs`（Swagger UI）、`/redoc`、`/openapi.json`

## 1. 约定

### 日期

- 所有日期参数/字段为 `YYYY-MM-DD`（ISO 8601）。
- 时间轴最早 `2012-11-08`（中共十八大），最晚为服务端当天；越界返回 `422`。
- 时间语义：**查询 `as_of` 当日在任**。包含代理与兼任；结束日期为 NULL 视为仍在任。
- 数据覆盖之外（`as_of > coverage_end`）仍返回最后已知状态，`coverage.beyond_coverage=true`，在任记录 `is_provisional=true`。

### 响应

成功响应直接返回资源对象，不额外套 `{data:...}`。错误统一：

```json
{
  "error": {
    "code": "not_found",
    "message": "region 999999 not found"
  }
}
```

参数校验错误：

```json
{
  "error": {
    "code": "validation_error",
    "message": "请求参数不合法",
    "details": [{"loc": ["query", "date"], "msg": "..."}]
  }
}
```

### 缓存

| Header | 说明 |
| --- | --- |
| `ETag` | 响应体 SHA-1 前 20 位强校验；支持 `If-None-Match` → `304` |
| `Cache-Control` | `public, max-age=60, stale-while-revalidate=300` |
| `X-Cache` | `HIT` / `MISS` / `STATIC`，便于观测 |

前端对快照按日期缓存 ETag；重复访问同一日期只传 304。

### 状态码

| 状态码 | 场景 |
| --- | --- |
| 200 | 成功 / 条件请求返回数据 |
| 304 | ETag 命中 |
| 404 | 省、官员、席位不存在 |
| 422 | 日期越界、分类非法、比较省份过多/为空 |
| 500 | 未捕获异常 |

## 2. 端点总表

| Method | Path | 缓存 | 说明 |
| --- | --- | --- | --- |
| GET | `/meta` | ✅ | 数据集、分类、指标、事件、GeoJSON 地址 |
| GET | `/events` | ✅ | 时间轴里程碑（静态） |
| GET | `/regions` | ✅ | 行政区划列表 |
| GET | `/map/snapshot` | ✅ | 31 省四套班子时点快照 |
| GET | `/regions/{code}/leaders` | ✅ | 单省时点详情 |
| GET | `/regions/{code}/timeline` | ✅ | 单省全部席位更替 |
| GET | `/regions/{code}/seats/{seat_key}/history` | ✅ | 单席位历任 |
| GET | `/officers` | ❌ | 官员检索 |
| GET | `/officers/{id}` | ❌ | 档案 + 当前职务 |
| GET | `/officers/{id}/career` | ✅ | 履历甘特图数据 + 状态事件 + 前后岗位 |
| GET | `/directory` | 30s | 官员名册表格（筛选/分页） |
| GET | `/coverage` | 60s | 当前/历史覆盖率与确认空缺 |
| GET | `/compare` | ✅ | 多省并置 |
| GET | `/health` | ❌ | 健康检查 |

---

## 3. `GET /meta`

无参数。返回前端启动所需的全部元信息。

```json
{
  "dataset": {
    "id": "2026.10",
    "coverage_start": "2012-11-08",
    "coverage_end": "2026-10-29",
    "plenum_date": "2026-10-29",
    "status": "demo",
    "counts": {"regions": 32, "officers": 332, "positions": 148, "tenures": 640, "events": 25}
  },
  "categories": [
    {"key": "party", "label": "党委", "order": 1, "accent": "#c0392b"}
  ],
  "metrics": [
    {"key": "party_days", "label": "党委书记在任天数", "unit": "天", "kind": "continuous"}
  ],
  "events": [
    {"date": "2012-11-08", "type": "congress", "label": "中共十八大", "description": "..."},
    {"date": "2026-10-29", "type": "congress", "label": "二十届五中全会", "description": "..."}
  ],
  "geo": {"geojson": "/geo/china-provinces.json", "adcode_property": "adcode", "name_property": "name"},
  "timezone": "Asia/Shanghai",
  "generated_at": "2026-11-13T18:00:00"
}
```

## 4. `GET /map/snapshot`

地图主数据源。一次返回 31 省，点击省份无需再请求。

**Query**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `date` | date | 否 | 默认今天 |
| `regions` | string | 否 | 逗号分隔 6 位代码，如 `110000,332000` |
| `categories` | string | 否 | `party,congress,government,cppcc` 子集 |

**Response（截断）**

```json
{
  "as_of": "2017-10-25",
  "coverage": {
    "dataset_id": "2026.10",
    "coverage_start": "2012-11-08",
    "coverage_end": "2026-10-29",
    "beyond_coverage": false,
    "status": "demo",
    "disclaimer": "本项目内置数据为产品演示用样例……"
  },
  "stats": {"region_count": 31, "member_count": 70, "acting_count": 2, "regions_with_gaps": 27},
  "regions": [
    {
      "region_code": "332000",
      "region_name": "上海市",
      "short_name": "上海",
      "level": "province",
      "centroid": [121.4737, 31.2304],
      "teams": {
        "party": {
          "key": "party",
          "label": "党委",
          "members": [
            {
              "tenure_id": 128,
              "officer": {"id": 64, "name": "李强", "slug": "p064", "gender": "M", "birth_year": 1959},
              "title": "上海市委书记",
              "category": "party",
              "seat_key": "party_secretary",
              "seat_rank": 1,
              "region_code": "332000",
              "region_name": "上海市",
              "rank_level": "provincial_principal",
              "rank_label": "副国级",
              "is_acting": false,
              "is_concurrent": false,
              "is_plural": false,
              "start_date": "2017-10-01",
              "end_date": "2022-09-30",
              "start_precision": "month",
              "duration_days": 25,
              "is_incumbent": false,
              "is_provisional": false,
              "is_roster_snapshot": false,
              "status": "left",
              "status_label": "已离任",
              "exit_reason": "transfer",
              "exit_reason_label": "调任",
              "verified": false
            }
          ]
        },
        "congress": {"key": "congress", "label": "人大", "members": []},
        "government": {"key": "government", "label": "政府", "members": []},
        "cppcc": {"key": "cppcc", "label": "政协", "members": []}
      },
      "headline": {
        "party": {"officer": {"name": "李强"}, "duration_days": 25},
        "government": {"officer": {"name": "应勇"}, "duration_days": 298},
        "congress": {"officer": {"name": "殷一璀"}, "duration_days": 1759},
        "cppcc": {"officer": {"name": "吴志明"}, "duration_days": 1759}
      },
      "filled": 4,
      "member_count": 4,
      "acting_count": 0,
      "metrics": {
        "party_days": 25,
        "governor_days": 304,
        "party_count": 2,
        "governor_count": 3,
        "filled": 4,
        "acting": 0
      }
    }
  ]
}
```

> `duration_days` 是**截至 `as_of`** 的在任天数，不是完整任期长度。完整任期在
> `/officers/{id}/career` 与席位历史中返回。

**curl**

```bash
curl -s "http://127.0.0.1:8000/api/v1/map/snapshot?date=2017-10-25&regions=332000" | jq
```

## 5. `GET /regions/{code}/leaders`

与快照中的单个 region 对象相同，外层包 `as_of / coverage / region`：

```json
{"as_of": "2017-10-25", "coverage": {...}, "region": { /* 同上 */ }}
```

## 6. `GET /regions/{code}/timeline`

该省所有席位在区间内的更替，用于全屏「四套班子席位更替」条带。

| 参数 | 说明 |
| --- | --- |
| `from` | 默认 `2012-11-08` |
| `to` | 默认数据覆盖截止日；超过覆盖范围会被 clamp |

```json
{
  "region_code": "332000",
  "region_name": "上海市",
  "from": "2012-11-08",
  "to": "2026-10-29",
  "lanes": [
    {
      "key": "party_secretary",
      "category": "party",
      "title": "市委书记",
      "label": "党委 · 市委书记",
      "rank": 1,
      "spans": [
        {"tenure_id": 126, "officer_name": "韩正", "start_date": "2012-11-01", "end_date": "2017-09-30", "duration_days": 1795, "is_acting": false}
      ]
    }
  ]
}
```

## 7. `GET /regions/{code}/seats/{seat_key}/history`

单个席位的完整任职序列，包含代理与空档。`seat_key` 取值：
`party_secretary` / `governor` / `congress_chair` / `cppcc_chair`。

**Query**：`date`（计算时长与现任的参照日）。

```json
{
  "region_code": "110000",
  "region_name": "北京市",
  "seat_key": "governor",
  "title": "市长",
  "category": "government",
  "as_of": "2026-10-29",
  "spans": [
    {
      "tenure_id": 12,
      "officer": {"id": 9, "name": "王安顺"},
      "title": "北京市市长",
      "start_date": "2012-07-01",
      "end_date": "2016-10-31",
      "duration_days": 1584,
      "is_acting": false,
      "gap_before_days": 0
    },
    {
      "tenure_id": 14,
      "officer": {"id": 7, "name": "蔡奇"},
      "title": "代市长",
      "start_date": "2016-10-01",
      "end_date": "2016-12-31",
      "duration_days": 92,
      "is_acting": true
    }
  ],
  "holder_count": 4,
  "acting_count": 4,
  "incumbent": {"officer": {"name": "殷勇"}, "start_date": "2023-01-01"}
}
```

> 席位史的 `duration_days` 是该段**完整任期**，不按查询日期截断；查询日期晚于某段结束时显示完整长度。若后继者在查询日期尚未到任，`is_future=true`，UI 显示“此后任职/尚未到任”，不再出现“不足 1 天”。`holder_count` 也只统计截至查询日已到任的正式任职。

## 8. `GET /officers`

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `q` | 空 | 姓名或籍贯模糊匹配，最长 32 字符 |
| `limit` | 20 | 1–50 |

返回 `Officer[]`（不含任职）。用于搜索面板。

## 9. `GET /officers/{id}`

**Query**：`date`（默认今天），返回该时点的当前职务。

```json
{
  "officer": {
    "id": 64, "name": "李强", "birth_year": 1959,
    "native_place": "浙江瑞安", "party_join_date": "1983-04-01",
    "work_start_date": "1976-07-01", "education": "研究生",
    "degree": "硕士", "bio": "曾任浙江省长、江苏省委书记、上海市委书记；2023年任国务院总理。"
  },
  "current": [{"title": "中央政治局常委", "region_code": null, "start_date": "2022-10-01"}],
  "stats": {"position_count": 5, "province_count": 3, "acting_count": 0,
            "first_start": "2012-12-01", "latest_end": "2026-10-29"},
  "as_of": "2026-10-29",
  "coverage": {...}
}
```

## 10. `GET /officers/{id}/career`

履历甘特图数据。按「地区/中央机构」分轨，每条 span 保留原始起止与时长。

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `from` | `2012-11-08` | |
| `to` | 数据覆盖截止日 | 会被 clamp，防止伪造未来 |

```json
{
  "officer": {"id": 64, "name": "李强"},
  "range": {"from": "2012-11-08", "to": "2026-10-29", "coverage_end": "2026-10-29", "requested_to": null},
  "lanes": [
    {"key": "330000", "label": "浙江", "full_label": "浙江省", "order": 0,
     "spans": [{"tenure_id": 301, "title": "浙江省长", "start_date": "2012-12-01",
                "end_date": "2016-05-31", "duration_days": 1278,
                "is_acting": false, "clipped_start": "2012-12-01"}]},
    {"key": "central", "label": "中央机构", "full_label": "中央 / 中央机构", "order": 99,
     "spans": [
       {"title": "中央政治局常委", "start_date": "2022-10-01", "end_date": null,
        "duration_days": 1003, "is_concurrent": false},
       {"title": "国务院总理", "start_date": "2023-03-01", "end_date": null,
        "duration_days": 853, "is_concurrent": false}
     ]}
  ],
  "summary": {"span_count": 5, "province_count": 3, "acting_count": 0, "total_days": 6407},
  "coverage": {...}
}
```

前端对同一轨内重叠的 span 自动分层（如中央政治局常委与国务院总理同时任职）。

## 11. `GET /compare`

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `regions` | 是 | 逗号分隔，1–6 个省 |
| `date` | 否 | 默认今天 |

返回与快照相同的 `RegionSnapshot` 数组：

```json
{"as_of": "2017-10-25", "coverage": {...}, "regions": [/* ... */]}
```

超过 6 个省或存在未知代码时分别返回 `422 invalid_range` / `404 not_found`。

## 12. `GET /directory`

与数据库同源的官员名册，供前端表格与 CSV 导出使用。

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `q` | 空 | 姓名/籍贯模糊匹配 |
| `region` | 空 | 省级代码 |
| `category` | 空 | `party/congress/government/cppcc/other` |
| `status` | 空 | `active/retired/under_investigation/expelled/deceased/left/unknown` |
| `rank` | 空 | 行政级别 key |
| `date` | 数据截止日 | 查询时点 |
| `page` / `page_size` | 1 / 50 | 最大 200 |

```json
{
  "items": [
    {
      "officer_id": 64,
      "name": "李强",
      "birth_year": 1959,
      "native_place": "浙江瑞安",
      "current_title": "国务院总理",
      "region_code": null,
      "region_name": null,
      "category": "other",
      "rank_level": "national_leader",
      "rank_label": "正国级",
      "start_date": "2023-03-01",
      "end_date": null,
      "start_precision": "month",
      "status": "active",
      "status_label": "在职",
      "previous_title": "中央政治局常委",
      "previous_rank_label": "正国级",
      "next_title": null,
      "next_rank_label": null,
      "source_count": 0,
      "verified": false,
      "updated_at": "2026-10-29"
    }
  ],
  "total": 332,
  "page": 1,
  "page_size": 50,
  "as_of": "2026-10-29",
  "dataset_version": "2026.10",
  "coverage": {...},
  "updated_at": "2026-10-29"
}
```

## 13. `GET /coverage`

完整率报告。返回当前时点四套正职覆盖率、确认空缺、历史检查点与分类覆盖。

```json
{
  "as_of": "2026-10-29",
  "dataset_version": "2026.10",
  "plenum_date": "2026-10-29",
  "provinces_total": 31,
  "provinces_complete": 31,
  "provinces_accounted": 31,
  "principal_coverage": 1.0,
  "principal_slots": 124,
  "principal_slots_filled": 124,
  "checkpoints": [
    {"date": "2012-11-08", "provinces_complete": 3, "principal_coverage": 0.0968},
    {"date": "2017-10-25", "provinces_complete": 31, "principal_coverage": 1.0},
    {"date": "2022-10-16", "provinces_complete": 31, "principal_coverage": 1.0},
    {"date": "2026-10-29", "provinces_complete": 31, "principal_coverage": 1.0}
  ],
  "vacancies": [],
  "tenures": 640,
  "officers": 332,
  "events": 25,
  "verified_tenures": 0,
  "verified_ratio": 0.0,
  "roster_snapshots": 72,
  "category_coverage": {
    "party": {"provinces": 31, "total": 31, "ratio": 1.0},
    "congress": {"provinces": 31, "total": 31, "ratio": 1.0},
    "government": {"provinces": 31, "total": 31, "ratio": 1.0},
    "cppcc": {"provinces": 31, "total": 31, "ratio": 1.0}
  },
  "regions": [...]
}
```

## 14. `GET /health`

```json
{
  "status": "ok",
  "repository": {"backend": "json", "dataset_id": "2026.10", "regions": 32, "officers": 332, "tenures": 640, "events": 25},
  "cache": {"layer": "memory", "items": 2, "hits": 1, "misses": 2, "hit_rate": 0.3333}
}
```

## 15. 规划中的端点

| Path | 说明 |
| --- | --- |
| `/map/snapshot?level=prefecture&parent=440000` | 地市下探 |
| `/officers/{id}/relations` | 同事/上下级关系图 |
| `/admin/tenures` (POST/PATCH) | 受控写入，带审计 |
| `/exports/snapshot.csv` | 研究用导出 |

## 16. 版本策略

当前为 `v1`，路径前缀固定 `/api/v1`。破坏性变更（字段删除/语义变化）升级到
`v2`；新增可选字段不升版本。所有响应示例见 `/openapi.json`。
