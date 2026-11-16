# 项目数据与架构规则

本文件是本项目后续开发的硬性规则。完整说明见
[docs/data-write-rules.md](docs/data-write-rules.md)。

## 唯一主数据

- `backend/app/data/dataset.json` 是唯一运行时主数据。
- 必须包含：officers、organizations、positions、tenures、identities、sources、position_equivalences、regions。
- 所有 API 必须从统一主数据读取人员、岗位、任职、身份。

## 生成数据

- `backend/app/data/central.json` 是构建产物，禁止手工编辑。
- 修改中央机构必须编辑 `scripts/central_seed.py`，然后执行：

```bash
python scripts/build_central.py
python scripts/import_central_officers.py
```

- 禁止在 `import_central_officers.py` 之后手改中央岗位或任期，否则会在下次导入时被覆盖。

## 标识

- 统一词汇表：`backend/app/data/vocabulary.json`。
- 届次、身份、级别、状态不得在页面或服务中另写一套中文映射。
- 身份标签必须由 `term + role` 生成；“原”只用于结束状态显示。
- 前端通过 `GET /api/v1/meta/vocabulary` 读取标签。
- 已发布 `position_uid` 和 `officer.id` 不得修改。

## 标识符规则

- `officers.id`、`officers.slug`、`positions.position_uid`、`seat_id`、`organization.id` 必须唯一且稳定。
- 禁止用姓名、标题、`seat_type` 作为身份键。
- 已发布的 ID 不得复用或重编号。
- 机构改名不换 ID；撤并保留 ID 并设置生命周期和继承关系。
- 一个机构两块牌子只建一个机构，用别名或 `position_equivalences` 表达。

## 时间与任期

- 日期统一 `YYYY-MM-DD`。
- `end_date` 包含当日。
- 禁止 `start_date > end_date`。
- 同一人同一岗位禁止重叠任期。
- 空缺不得伪造人员。
- 代理、兼任、多人岗位必须分别标记 `is_acting`、`is_concurrent`、`is_plural`。
- 时间轴节点统一使用会议**闭幕日**：党代会、全国人大会议、中央全会均不得使用开幕日。
- 当前时间轴不加入党代会节点；保留中央全会节点，并加入各届全国人大第一次会议节点。
- 全国人大节点必须使用 `type: "npc"`，与中央全会的 `type: "plenum"` 在 UI 上区分。
- 新增时间节点必须同时写明会期和闭幕日，并在描述中包含“闭幕”。
- 中央领导机构换届必须在大会一中全会闭幕日之后；二十届领导机构任期自 `2022-10-23` 起算。
- 中央机构侧栏届次按钮必须指向一中全会闭幕日：十八届 `2012-11-15`、十九届 `2017-10-25`、二十届 `2022-10-23`。
- 中央机构详情在任一历史时点必须保留尚未到任的任职记录，但标记 `尚未到任`，并使用虚线/低透明度 UI 与在任记录区分；在任时长截至当前时间节点。
- 任职起止日期必须显示数据中的明确日期，不得因时间轴切换而改成“至今”或未来日期；只有缺失结束日期时才显示“至今”。

## 写入流程

任何新增或修改必须：

1. 先确认人员、机构、岗位 ID；
2. 写岗位后再写任职；
3. 每条任职必须有 `officer_id`、`position_id`、`start_date`、`source_id`；
4. 党内身份写入 `identities`，不得写进岗位或人员姓名；
5. 使用原子写入替换 JSON；
6. 运行校验与测试。

## 必跑校验

```bash
python scripts/validate_all.py
cd backend && pytest -q
cd ../frontend && pnpm build
```

`validate_all.py` 会依次运行：

- `validate_schema.py`
- `validate_dataset.py`
- `validate_central.py`

校验必须为 0 问题；测试必须全通过。CI 配置见 `.github/workflows/ci.yml`。

## 前端

前端禁止按标题去重、按姓名合并、自己拼接岗位名或自己判断政治局层级。
前端只使用后端返回的 `officer_id`、`position_uid`、`seat_id`、`tenure_id`。

## 信源

- Wikipedia 仅作线索，不作为最终权威。
- `verified=true` 必须有官方或官方媒体来源。
- 无来源只能标记 provisional 或 unverified。
- 禁止编造任职、日期、出生年、籍贯。

## 禁止事项

- 禁止直接编辑 `central.json`。
- 禁止修改已发布的 `position_uid`。
- 禁止按姓名合并人员。
- 禁止删除仍有关联任职的岗位。
- 禁止新增无 `source_id` 的任职。
- 禁止绕过校验直接改生产数据。

规则版本：v1.0。规则变更必须修改本文件和
`docs/data-write-rules.md`，并经过测试与评审。
