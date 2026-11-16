# 机构信息统一接口

## 目标

机构信息抽屉（`InstitutionDrawer`）只依赖统一机构详情契约，不区分中央与地方。

## 端点

```text
GET /api/v1/institutions/{entity_type}/{institution_id}?date=YYYY-MM-DD
```

`entity_type`：

```text
central
province
prefecture
county
subordinate
```

## 当前实现

- `central`：由 `central_service.institution()` 适配；
- `province` / `prefecture` / `county` / `subordinate`：接口路径已保留，适配器尚未接入，当前返回：

```json
{
  "detail": {
    "code": "institution_adapter_not_available",
    "message": "province 机构适配器尚未接入统一数据源"
  }
}
```

## 响应契约

```json
{
  "schema_version": 1,
  "entity_type": "central",
  "id": "party:central_committee",
  "name": "中国共产党中央委员会",
  "short_name": "中央委员会",
  "institution_type": "party_leadership",
  "institution_rank": "national_leader",
  "status_at": "active",
  "aliases": [],
  "parent_id": null,
  "created_at": "2012-11-08",
  "leaders": [],
  "history": [],
  "children": [],
  "sections": [
    { "key": "overview", "label": "概况", "available": true },
    { "key": "leaders", "label": "领导班子", "available": true },
    { "key": "history", "label": "机构沿革", "available": false },
    { "key": "roster", "label": "中央委员会名单", "available": true },
    { "key": "children", "label": "下属机构", "available": true }
  ]
}
```

## 前端规则

- 只根据 `sections[].available` 决定是否显示分区；
- 不根据 `entity_type` 写分支；
- 地方机构缺少 `roster` 时不显示“中央委员会名单”；
- 下属机构通过 `children` 或机构树的 `parent_id` 进入同一抽屉；
- 返回时使用抽屉内栈或父机构回退，不重新创建抽屉。

## 地方数据接入要求

每个地方适配器至少需要：

```text
id
parent_id
name
short_name
institution_type
institution_rank
level
status
created_at
leaders
history
children
```

同时提供：

```text
source_id
verification_status
as_of
```

无来源字段不得伪造；没有机构沿革数据时 `history.available = false`。

## 兼容性

旧端点：

```text
GET /api/v1/central/institutions/{id}
```

继续保留；前端已切换到新端点。

## 测试

- `test_institution_contract_endpoint`；
- 静态校验 `validate_all.py`；
- 前端构建。
