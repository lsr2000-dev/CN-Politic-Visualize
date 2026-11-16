# 数据写入与架构规则 v1.0

本规则是项目的数据写入、导入、迁移和发布基线。  
`AGENTS.md` 是摘要，本文件是完整说明。

## 1. 单一主数据

唯一运行时主数据：

```text
backend/app/data/dataset.json
```

必须包含：

```text
officers
organizations
positions
tenures
identities
sources
position_equivalences
regions
```

`central.json` 是构建产物，不是手工维护文件。

## 2. 数据所有权

| 数据 | 来源 |
|---|---|
| 人员 | dataset.json |
| 省级机构/岗位/任职 | dataset.json |
| 中央机构结构 | scripts/central_seed.py → central.json → dataset.json |
| 中央岗位/任职 | scripts/central_seed.py → central.json → import → dataset.json |
| 党内身份 | dataset.json identities |
| 信源 | dataset.json sources |

禁止直接编辑 `central.json`。

## 3. 标准构建顺序

```bash
python scripts/build_central.py
python scripts/import_central_officers.py
python scripts/validate_dataset.py
python scripts/validate_central.py
cd backend && pytest -q
cd ../frontend && pnpm build
```

顺序不可颠倒。

- 只改省级数据：允许直接改 dataset，但必须跑校验和测试。
- 改中央机构：必须改 `central_seed.py`，然后 build + import。
- import 会重建中央岗位、任期、身份，并覆盖手改内容。

## 4. 标识符

### 人员

- `officers.id` 全局唯一、永不复用。
- `officers.slug` 全局唯一、稳定。
- 姓名不是身份键；禁止按姓名合并人员。

### 岗位

- `positions.position_uid` 全局唯一。
- 省级格式：`{region_code}:{seat_key}`。
- 中央格式：`central:{institution_id}:seat:{hash}`。
- 发布后不可修改、不可复用。

### 中央席位

- `seat_id` 表示完整岗位。
- 部长、党组书记、党委书记必须是不同 seat。
- 禁止用 `seat_type` 作为岗位唯一键。

### 机构

- `organization.id` 稳定。
- 改名不换 ID。
- 撤并保留 ID，设置 `valid_to`、`status`、`successor_id`。

## 5. 时间与任期

- 日期统一 `YYYY-MM-DD`。
- `end_date` 包含当日。
- 禁止 `start_date > end_date`。
- 同一人同一岗位禁止重叠。
- 允许连续任期；展示层可合并。
- 空缺不得伪造人员。
- 代理、兼任、多人岗位必须标记：

```text
is_acting
is_concurrent
is_plural
```

### 时间节点

- 党代会、全国人大会议、中央全会等时间轴节点，统一使用**闭幕日**。
- 当前时间轴不加入党代会节点；保留中央全会节点，并加入各届全国人大第一次会议节点。
- 全国人大节点使用 `type: "npc"`；中央全会使用 `type: "plenum"`，前端必须用不同样式区分。
- 不再加入七中全会节点。
- 禁止使用开幕日作为 `TIMELINE_EVENTS` 的 `date`。
- 新节点必须记录完整会期，并在描述中写明“闭幕”。
- 中央领导机构换届必须在大会一中全会闭幕日之后；二十届领导机构任期自 `2022-10-23` 起算。
- 中央机构侧栏届次按钮必须指向一中全会闭幕日：十八届 `2012-11-15`、十九届 `2017-10-25`、二十届 `2022-10-23`。
- 中央机构详情在任一历史时点必须保留尚未到任的任职记录，但标记 `尚未到任`，并使用虚线/低透明度 UI 与在任记录区分；在任时长截至当前时间节点。
- 任职起止日期必须显示数据中的明确日期，不得因时间轴切换而改成“至今”或未来日期；只有缺失结束日期时才显示“至今”。
- 例如：二十大 2022-10-16 开幕、10-22 闭幕，系统节点为 `2022-10-22`。

## 6. 新增人员

流程：

1. 按姓名、出生年、籍贯查重；
2. 确认不是已有人员；
3. 分配新 `id` 和唯一 `slug`；
4. 写 officers；
5. 再写任职。

必填：

```text
id, slug, name, birth_year, native_place
```

出生年份必须在 `1920–2000`，籍贯必须是非空中文地名。

禁止：

- 用空 ID 占位；
- 修改已有人员 ID；
- 删除仍有关联任职的人员；
- 同名自动合并。

## 7. 新增岗位

岗位必须包含：

```text
id
organization_id
code
title
full_title
position_uid
position_kind
rank
is_principal
is_plural
valid_from
valid_to
display_order
```

`position_kind`：

```text
leadership_singleton
leadership_collective
functional
committee_membership
honorary
```

规则：

- 一个完整岗位一个 UID。
- 岗位改名不换 UID。
- 标题变化通过别名/显示标题处理。
- 一个机构两块牌子只建一个岗位。

## 8. 新增任职

任职必须包含：

```text
officer_id
position_id
start_date
end_date
source_id
```

禁止：

- 用姓名代替 officer_id；
- 用 seat_key 代替 position_id；
- 无 source_id 写入；
- 同一人同一岗位重叠；
- 无来源标 verified。

## 9. 党内身份

身份单独写入 `identities`：

```text
person_id
term
term_label
role
label
start_date
end_date
source
```

规则：

- 按届次区分；
- 同一届同一角色不能重复；
- 身份变化关闭旧身份、新增新身份；
- 不得用岗位名称代替身份；
- 政治局常委、委员、书记处书记分别记录。

## 10. 机构

机构必须包含：

```text
id
parent_id
team
category
name
short_name
rank
valid_from
valid_to
status
```

规则：

- 改名不换 ID；
- 撤并保留 ID；
- 未成立前不得有任职；
- 一个机构两块牌子只建一个机构；
- 合署办公明确主机构和别名；
- 禁止重复建节点。

## 11. 信源

信源等级：

```text
A official
B official_media
C wikipedia
D unverified
```

规则：

- A/B 可 `verified=true`；
- C 默认 provisional；
- D 不进入正式统计；
- Wikipedia 只作线索，必须找原始官方来源；
- 修改任期保留旧源。

禁止编造任职、日期、出生年、籍贯。

## 12. 热更新

写入必须原子替换：

```text
临时文件 → fsync → os.replace
```

API 行为：

```text
mtime 变化
→ dataset_version 更新
→ 重新加载
→ 缓存键变化
→ 旧缓存失效
```

响应头：

```text
X-Data-Version
Cache-Control: no-cache
```

验收接口：

```text
官员详情
中央机构详情
履历
名册
搜索
```

都要立即返回新数据。

## 13. 校验

每次写入必须通过：

```text
officer id 唯一
slug 唯一
position_uid 唯一
tenure 外键存在
source_id 存在
start <= end
同人同岗位无重叠
机构父子存在
机构生命周期合法
中央负责人有 officer_id / position_uid
岗位等价 UID 存在
```

脚本：

```bash
python scripts/validate_all.py
```

它依次执行：

```text
validate_schema.py
validate_dataset.py
validate_central.py
```

CI 配置：

```text
.github/workflows/ci.yml
```

## 14. 前端

禁止：

- 按标题去重；
- 按姓名匹配；
- 前端拼接岗位名；
- 前端判断政治局层级；
- 前端本地缓存覆盖 API。

只使用：

```text
officer_id
position_uid
seat_id
tenure_id
```

## 15. 禁止事项

```text
直接编辑 central.json
修改已发布 position_uid
修改 officer.id
按姓名合并人员
按标题删除岗位
删除仍有关联任职的岗位
新增无 source_id 的任职
新增 start > end 的任期
用 seat_type 代替岗位 ID
import 后手改中央岗位
绕过校验直接改数据
```

## 16. 提交检查表

- [ ] 未直接编辑 central.json
- [ ] 新人员有唯一 id/slug
- [ ] 新岗位有唯一 position_uid
- [ ] 新任职有 officer_id/position_id/source_id
- [ ] 任期合法且不重叠
- [ ] 机构生命周期合法
- [ ] 未按姓名/标题合并
- [ ] 中央数据已 build + import
- [ ] validate_dataset.py 通过
- [ ] validate_central.py 通过
- [ ] 后端测试通过
- [ ] 前端构建通过
- [ ] 热更新验证通过

## 17. 当前基线

```text
816 名官员
357 个岗位
1527 条任职
160 条党内身份
260 个中央机构节点
```

校验：

```text
0 个结构问题
0 个任期重叠
0 个 position_uid 缺失
0 个 position_uid 重复
```

测试：

```text
35 passed
```

规则变更必须更新本文件与 `AGENTS.md`，并经过测试与评审。
