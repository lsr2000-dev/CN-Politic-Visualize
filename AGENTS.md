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

## 标识符

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
