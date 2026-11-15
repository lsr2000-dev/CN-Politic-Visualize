-- =====================================================================
--  十八大以来中国地方政治人事时空可视化系统
--  PostgreSQL 16 + PostGIS 3.4  —  Core schema
-- ---------------------------------------------------------------------
--  设计原则
--  1. 事实表 tenures 采用「区间事实」建模：一条记录 = 某人某岗的一段
--     连续任职；结束时间为 NULL 表示仍在任。所有时间切片查询都归结为
--     daterange 的包含判断，可命中 GiST 索引。
--  2. positions 是「席位注册表」（seat registry），不随人变化；
--     tenures 中冗余保存 title / category / region_code 作为写入时的
--     快照，保证历史名称变更后旧记录仍可正确展示。
--  3. 代理（is_acting）与兼任（is_concurrent）是独立维度，不污染
--     正式任职的唯一性约束。
--  4. 每一条任职都可回溯到公开来源（sources / tenure_sources），
--     并以 verified 标记人工复核状态，满足政治类数据的可审计要求。
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS btree_gist;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE SCHEMA IF NOT EXISTS polvis;
COMMENT ON SCHEMA polvis IS '地方政治人事时空数据仓库';

SET search_path = polvis, public;

-- ---------------------------------------------------------------------
-- 枚举
-- ---------------------------------------------------------------------
DO $$ BEGIN
  CREATE TYPE polvis.region_level AS ENUM ('country', 'province', 'prefecture', 'county');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE polvis.position_category AS ENUM ('party', 'congress', 'government', 'cppcc', 'other');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE polvis.date_precision AS ENUM ('day', 'month', 'year', 'snapshot');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE polvis.appointment_type AS ENUM ('elected', 'appointed', 'acting', 'co_opted', 'concurrent');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE polvis.position_rank_level AS ENUM (
    'national_leader', 'vice_national_leader', 'ministerial', 'vice_ministerial',
    'provincial_principal', 'provincial_deputy', 'bureau', 'unknown'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE polvis.tenure_end_reason AS ENUM (
    'promotion', 'transfer', 'retirement', 'term_end', 'removed',
    'investigation', 'expulsion', 'death', 'acting_end', 'restructure', 'unknown'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE polvis.officer_event_type AS ENUM (
    'retired', 'under_investigation', 'expelled_from_party',
    'expelled_from_public_office', 'removed_from_office', 'deceased',
    'appointed', 'transferred', 'other'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ---------------------------------------------------------------------
-- regions 行政区划
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS polvis.regions (
    code          varchar(12) PRIMARY KEY,                 -- GB/T 2260 行政区划代码
    name          text        NOT NULL,                    -- 北京市
    short_name    text,                                    -- 北京
    level         polvis.region_level NOT NULL,
    parent_code   varchar(12) REFERENCES polvis.regions (code),
    centroid      geometry(Point, 4326),                   -- 代表点，用于标签与就近查询
    geom          geometry(MultiPolygon, 4326),            -- 边界，用于 PostGIS 空间检索
    bbox          geometry(Polygon, 4326),
    sort_order    smallint    NOT NULL DEFAULT 0,
    is_active     boolean     NOT NULL DEFAULT true,
    valid_from    date        NOT NULL DEFAULT DATE '1949-10-01',
    valid_to      date,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT regions_parent_chk CHECK (
        (level = 'country' AND parent_code IS NULL)
        OR (level <> 'country' AND parent_code IS NOT NULL)
    )
);

COMMENT ON TABLE polvis.regions IS '行政区划（国/省/地市），几何字段使用 WGS84，展示时可前端投影';
COMMENT ON COLUMN polvis.regions.code IS 'GB/T 2260 代码；省级 6 位，地市级 6 位，国家 100000';

CREATE INDEX IF NOT EXISTS regions_geom_gix   ON polvis.regions USING gist (geom);
CREATE INDEX IF NOT EXISTS regions_parent_idx ON polvis.regions (parent_code, level, sort_order);
CREATE INDEX IF NOT EXISTS regions_name_trgm  ON polvis.regions USING gin (name gin_trgm_ops);

-- ---------------------------------------------------------------------
-- officers 官员主表
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS polvis.officers (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    slug            text        NOT NULL UNIQUE,           -- 稳定 URL 标识：cai-qi
    name            text        NOT NULL,
    name_en         text,
    gender          char(1)     CHECK (gender IN ('M', 'F') OR gender IS NULL),
    birth_date      date,
    birth_year      smallint    CHECK (birth_year BETWEEN 1900 AND 2015),
    native_place    text,                                  -- 籍贯
    ethnicity       text,                                  -- 民族
    party_join_date date,                                  -- 入党时间
    work_start_date date,                                  -- 参加工作
    education       text,
    degree          text,
    school          text,
    portrait_url    text,
    bio             text,                                  -- 120 字以内摘要
    wikidata_id     text,
    is_deceased     boolean     NOT NULL DEFAULT false,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE polvis.officers IS '官员主表；同名不同人通过 slug 区分，导入时需人工消歧';

CREATE INDEX IF NOT EXISTS officers_name_trgm ON polvis.officers USING gin (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS officers_birth_idx ON polvis.officers (birth_year);

-- ---------------------------------------------------------------------
-- positions 席位注册表（岗位定义，而非某人的任职）
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS polvis.positions (
    id                 bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    seat_key           text        NOT NULL,               -- party_secretary / governor / congress_chair / cppcc_chair
    region_code        varchar(12) REFERENCES polvis.regions (code) ON DELETE CASCADE,
    category           polvis.position_category NOT NULL,
    title              text        NOT NULL,               -- 省委书记
    full_title         text,                               -- 中共北京市委书记
    rank               smallint    NOT NULL DEFAULT 1,     -- 班子内排序，书记=1
    rank_level         polvis.position_rank_level NOT NULL DEFAULT 'provincial_principal',
    team_group         text,                               -- party_standco / gov_deputy / npc_deputy / cppcc_deputy
    is_singular        boolean     NOT NULL DEFAULT true,  -- false = 多成员岗位（常委/副职）
    is_leader          boolean     NOT NULL DEFAULT true,  -- 是否「一把手」
    parent_position_id bigint REFERENCES polvis.positions (id),
    org_name           text,                               -- 中央/其他机构岗位
    valid_from         date        NOT NULL DEFAULT DATE '1949-10-01',
    valid_to           date,
    created_at         timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT positions_dates_chk CHECK (valid_to IS NULL OR valid_to >= valid_from)
);

COMMENT ON TABLE polvis.positions IS '岗位/席位注册表；每个省的每类班子可挂多个席位（书记、副书记…）';

-- 允许 region_code 为 NULL（中央岗位），因此不能用普通 UNIQUE 约束
CREATE UNIQUE INDEX IF NOT EXISTS positions_seat_uk
    ON polvis.positions (COALESCE(region_code, '000000'), seat_key, valid_from);
CREATE INDEX IF NOT EXISTS positions_region_idx ON polvis.positions (region_code, category, rank);

-- ---------------------------------------------------------------------
-- dataset_versions 数据版本（同时作为 Redis 缓存命名空间）
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS polvis.dataset_versions (
    id            text PRIMARY KEY,                        -- 2025.06
    coverage_start date       NOT NULL DEFAULT DATE '2012-11-08',
    coverage_end  date        NOT NULL,
    status        text        NOT NULL DEFAULT 'draft'
                  CHECK (status IN ('draft', 'published', 'archived')),
    notes         text,
    published_at  timestamptz,
    created_at    timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- sources 公开来源
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS polvis.sources (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title        text        NOT NULL,
    publisher    text,                                     -- 新华社 / 人民日报 / 中国经济网
    url          text,
    archive_url  text,
    published_on date,
    retrieved_at timestamptz NOT NULL DEFAULT now(),
    reliability  smallint    NOT NULL DEFAULT 2 CHECK (reliability BETWEEN 1 AND 3),
    CONSTRAINT sources_url_uk UNIQUE (url)
);

-- ---------------------------------------------------------------------
-- tenures 任职履历明细（核心事实表）
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS polvis.tenures (
    id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    officer_id        bigint      NOT NULL REFERENCES polvis.officers (id) ON DELETE RESTRICT,
    position_id       bigint      NOT NULL REFERENCES polvis.positions (id) ON DELETE RESTRICT,
    region_code       varchar(12) REFERENCES polvis.regions (code),
    category          polvis.position_category NOT NULL,
    title             text        NOT NULL,               -- 写入时快照，例如「代省长」
    start_date        date        NOT NULL,
    end_date          date,                               -- NULL = 仍在任
    start_precision   polvis.date_precision NOT NULL DEFAULT 'day',
    end_precision     polvis.date_precision,
    is_acting         boolean     NOT NULL DEFAULT false,  -- 代省长 / 代市长 / 主持工作
    is_concurrent     boolean     NOT NULL DEFAULT false,  -- 兼任（如省委书记兼人大主任）
    is_plural         boolean     NOT NULL DEFAULT false,  -- 多成员岗位（常委/副职），不参与排他
    rank_level_snapshot polvis.position_rank_level NOT NULL DEFAULT 'provincial_deputy',
    end_reason        polvis.tenure_end_reason,
    end_reason_detail text,
    appointment_type  polvis.appointment_type,
    appointment_basis text,                               -- 省人大常委会第 N 次会议决定
    successor_id      bigint REFERENCES polvis.tenures (id),
    dataset_version   text        REFERENCES polvis.dataset_versions (id),
    verified          boolean     NOT NULL DEFAULT false,
    notes             text,
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now(),
    -- 规范化为半开区间 [start, end+1)，避免「同日交接」被误判为重叠
    period            daterange GENERATED ALWAYS AS
                      (daterange(start_date, end_date + 1, '[)')) STORED,
    CONSTRAINT tenures_dates_chk CHECK (end_date IS NULL OR end_date >= start_date),
    CONSTRAINT tenures_successor_chk CHECK (successor_id IS NULL OR successor_id <> id)
);

COMMENT ON TABLE  polvis.tenures IS '任职事实表：一行 = 一人一岗一段连续任职';
COMMENT ON COLUMN polvis.tenures.period IS '生成列，半开区间；所有时点切片查询使用 period @> date';
COMMENT ON COLUMN polvis.tenures.is_acting IS '代理任职，与正式任职并存展示，但不占用席位唯一性';

-- 同一席位、正式任职的时间区间不允许重叠；兼任与代理不受此约束
ALTER TABLE polvis.tenures
    DROP CONSTRAINT IF EXISTS tenures_seat_no_overlap;
ALTER TABLE polvis.tenures
    ADD CONSTRAINT tenures_seat_no_overlap
    EXCLUDE USING gist (position_id WITH =, period WITH &&)
    WHERE (is_acting = false AND is_concurrent = false AND is_plural = false);

-- 同一席位最多一条「在任」正式记录
CREATE UNIQUE INDEX IF NOT EXISTS tenures_one_open_uk
    ON polvis.tenures (position_id)
    WHERE end_date IS NULL AND is_acting = false AND is_concurrent = false AND is_plural = false;

CREATE INDEX IF NOT EXISTS tenures_period_gix  ON polvis.tenures USING gist (period);
CREATE INDEX IF NOT EXISTS tenures_region_gix  ON polvis.tenures USING gist (region_code, period);
CREATE INDEX IF NOT EXISTS tenures_officer_idx ON polvis.tenures (officer_id, start_date DESC);
CREATE INDEX IF NOT EXISTS tenures_open_idx    ON polvis.tenures (region_code) WHERE end_date IS NULL;
CREATE INDEX IF NOT EXISTS tenures_category_idx ON polvis.tenures (category, region_code, start_date DESC);

-- ---------------------------------------------------------------------
-- tenure_sources 多对多来源关联
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS polvis.tenure_sources (
    tenure_id bigint NOT NULL REFERENCES polvis.tenures (id) ON DELETE CASCADE,
    source_id bigint NOT NULL REFERENCES polvis.sources (id) ON DELETE CASCADE,
    note      text,
    PRIMARY KEY (tenure_id, source_id)
);

-- ---------------------------------------------------------------------
-- officer_events 任职之外的状态事件（退休/审查/处分/病逝等）
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS polvis.officer_events (
    id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    officer_id        bigint NOT NULL REFERENCES polvis.officers (id) ON DELETE RESTRICT,
    event_type        polvis.officer_event_type NOT NULL,
    event_date        date NOT NULL,
    title             text NOT NULL,
    description       text,
    related_tenure_id bigint REFERENCES polvis.tenures (id) ON DELETE SET NULL,
    source_id         bigint REFERENCES polvis.sources (id) ON DELETE SET NULL,
    source_url        text,
    source_title      text,
    verified          boolean NOT NULL DEFAULT false,
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE polvis.officer_events IS
'退休、接受纪律审查、开除党籍/公职、病逝等非任职事件；只记录官方公开信息';

CREATE INDEX IF NOT EXISTS officer_events_officer_idx
    ON polvis.officer_events (officer_id, event_date DESC);
CREATE INDEX IF NOT EXISTS officer_events_type_idx
    ON polvis.officer_events (event_type, event_date DESC);

-- ---------------------------------------------------------------------
-- change_log 审计日志（数据修正必须留痕）
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS polvis.change_log (
    id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    table_name text        NOT NULL,
    row_id     bigint,
    action     text        NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE')),
    diff       jsonb,
    actor      text        NOT NULL DEFAULT current_user,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS change_log_target_idx ON polvis.change_log (table_name, row_id, created_at DESC);

-- ---------------------------------------------------------------------
-- 通用触发器
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION polvis.touch_updated_at() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS regions_touch ON polvis.regions;
CREATE TRIGGER regions_touch BEFORE UPDATE ON polvis.regions
    FOR EACH ROW EXECUTE FUNCTION polvis.touch_updated_at();

DROP TRIGGER IF EXISTS officers_touch ON polvis.officers;
CREATE TRIGGER officers_touch BEFORE UPDATE ON polvis.officers
    FOR EACH ROW EXECUTE FUNCTION polvis.touch_updated_at();

DROP TRIGGER IF EXISTS tenures_touch ON polvis.tenures;
CREATE TRIGGER tenures_touch BEFORE UPDATE ON polvis.tenures
    FOR EACH ROW EXECUTE FUNCTION polvis.touch_updated_at();

DROP TRIGGER IF EXISTS officer_events_touch ON polvis.officer_events;
CREATE TRIGGER officer_events_touch BEFORE UPDATE ON polvis.officer_events
    FOR EACH ROW EXECUTE FUNCTION polvis.touch_updated_at();

CREATE OR REPLACE FUNCTION polvis.log_tenure_change() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO polvis.change_log (table_name, row_id, action, diff)
    VALUES (
        'tenures',
        COALESCE(NEW.id, OLD.id),
        TG_OP,
        CASE
            WHEN TG_OP = 'UPDATE' THEN
                jsonb_build_object(
                    'before', to_jsonb(OLD) - 'created_at' - 'updated_at',
                    'after',  to_jsonb(NEW) - 'created_at' - 'updated_at'
                )
            WHEN TG_OP = 'DELETE' THEN to_jsonb(OLD)
            ELSE to_jsonb(NEW)
        END
    );
    RETURN COALESCE(NEW, OLD);
END $$;

DROP TRIGGER IF EXISTS tenures_audit ON polvis.tenures;
CREATE TRIGGER tenures_audit AFTER INSERT OR UPDATE OR DELETE ON polvis.tenures
    FOR EACH ROW EXECUTE FUNCTION polvis.log_tenure_change();

-- ---------------------------------------------------------------------
-- 视图：任职展开（带任期天数与在任标记）
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW polvis.v_tenure_expanded AS
SELECT
    t.id                                             AS tenure_id,
    t.officer_id,
    o.name                                           AS officer_name,
    o.slug                                           AS officer_slug,
    o.gender,
    o.birth_year,
    t.position_id,
    p.seat_key,
    p.rank                                           AS seat_rank,
    p.is_leader,
    t.region_code,
    r.name                                           AS region_name,
    r.short_name                                     AS region_short_name,
    t.category,
    t.title,
    p.full_title,
    p.org_name,
    t.rank_level_snapshot,
    t.is_plural,
    t.end_reason,
    t.end_reason_detail,
    t.start_date,
    t.end_date,
    t.start_precision,
    t.end_precision,
    t.is_acting,
    t.is_concurrent,
    t.verified,
    t.notes,
    t.successor_id,
    t.period,
    (COALESCE(upper(t.period), CURRENT_DATE + 1) - lower(t.period)) AS duration_days,
    (t.end_date IS NULL)                             AS is_incumbent
FROM polvis.tenures t
JOIN polvis.officers  o ON o.id = t.officer_id
JOIN polvis.positions p ON p.id = t.position_id
LEFT JOIN polvis.regions r ON r.code = t.region_code;

COMMENT ON VIEW polvis.v_tenure_expanded IS '任职事实 + 官员/岗位/地区冗余，API 主要读取对象';

-- ---------------------------------------------------------------------
-- 视图：官员名册（当前/最后职务 + 状态），供人类可读表格与 SQL 查询
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW polvis.v_officer_directory AS
WITH latest AS (
    SELECT DISTINCT ON (v.officer_id)
           v.officer_id, v.tenure_id, v.title, v.region_code, v.region_name,
           v.category, v.seat_key, v.start_date, v.end_date,
           v.rank_level_snapshot, v.is_acting, v.verified, v.is_plural
    FROM polvis.v_tenure_expanded v
    ORDER BY v.officer_id, v.start_date DESC, v.tenure_id DESC
),
latest_event AS (
    SELECT DISTINCT ON (e.officer_id)
           e.officer_id, e.event_type, e.event_date, e.title
    FROM polvis.officer_events e
    ORDER BY e.officer_id, e.event_date DESC, e.id DESC
)
SELECT
    o.id                                              AS officer_id,
    o.name,
    o.gender,
    o.birth_year,
    o.native_place,
    l.title                                           AS last_title,
    l.region_code,
    l.region_name,
    l.category,
    l.start_date,
    l.end_date,
    l.rank_level_snapshot                             AS rank_level,
    CASE
        WHEN e.event_type IN ('expelled_from_party', 'expelled_from_public_office') THEN 'expelled'
        WHEN e.event_type = 'under_investigation' THEN 'under_investigation'
        WHEN e.event_type = 'retired' THEN 'retired'
        WHEN e.event_type = 'deceased' THEN 'deceased'
        WHEN l.tenure_id IS NULL THEN 'unknown'
        WHEN l.end_date IS NULL THEN 'active'
        ELSE 'left'
    END                                               AS status,
    e.event_date                                      AS status_date,
    e.title                                           AS status_title,
    COALESCE((
        SELECT count(*)
        FROM polvis.tenure_sources ts
        JOIN polvis.tenures tt ON tt.id = ts.tenure_id
        WHERE tt.officer_id = o.id
    ), 0)                                             AS source_count,
    o.updated_at
FROM polvis.officers o
LEFT JOIN latest l ON l.officer_id = o.id
LEFT JOIN latest_event e ON e.officer_id = o.id;

COMMENT ON VIEW polvis.v_officer_directory IS
'一行一个官员：当前/最后职务、级别、状态、来源数；用于名册表格与直接 SQL 查询';

-- ---------------------------------------------------------------------
-- 函数：指定日期的省级班子切片
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION polvis.fn_snapshot(
    p_date        date,
    p_region_codes varchar[] DEFAULT NULL
)
RETURNS TABLE (
    region_code   varchar(12),
    region_name   text,
    category      polvis.position_category,
    seat_key      text,
    seat_rank     smallint,
    tenure_id     bigint,
    officer_id    bigint,
    officer_name  text,
    title         text,
    start_date    date,
    end_date      date,
    is_acting     boolean,
    is_concurrent boolean,
    duration_days integer
)
LANGUAGE sql STABLE AS $$
    SELECT v.region_code, v.region_name, v.category, v.seat_key, v.seat_rank,
           v.tenure_id, v.officer_id, v.officer_name, v.title,
           v.start_date, v.end_date, v.is_acting, v.is_concurrent,
           v.duration_days
    FROM polvis.v_tenure_expanded v
    WHERE v.period @> p_date
      AND v.region_code IS NOT NULL
      AND (p_region_codes IS NULL OR v.region_code = ANY (p_region_codes))
      AND v.category IN ('party', 'congress', 'government', 'cppcc')
    ORDER BY v.region_code, v.category, v.seat_rank;
$$;

COMMENT ON FUNCTION polvis.fn_snapshot IS '时点切片：返回某日所有（或指定）省份四套班子在任记录，含代理/兼任';

-- ---------------------------------------------------------------------
-- 函数：某日空缺席位（用于首页缺口提示 / 数据质量看板）
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION polvis.fn_vacant_seats(p_date date)
RETURNS TABLE (region_code varchar(12), category polvis.position_category, seat_key text, title text)
LANGUAGE sql STABLE AS $$
    SELECT p.region_code, p.category, p.seat_key, p.title
    FROM polvis.positions p
    JOIN polvis.regions r ON r.code = p.region_code AND r.level = 'province'
    WHERE p.is_leader
      AND NOT EXISTS (
          SELECT 1 FROM polvis.tenures t
          WHERE t.position_id = p.id AND t.period @> p_date
      )
    ORDER BY p.region_code, p.category;
$$;

-- ---------------------------------------------------------------------
-- 函数：官员履历（跨省/跨部门），供甘特图直接消费
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION polvis.fn_career(
    p_officer_id bigint,
    p_from       date DEFAULT DATE '2012-11-08',
    p_to         date DEFAULT CURRENT_DATE
)
RETURNS TABLE (
    tenure_id    bigint,
    region_code  varchar(12),
    region_name  text,
    category     polvis.position_category,
    title        text,
    start_date   date,
    end_date     date,
    duration_days integer,
    is_acting    boolean,
    is_concurrent boolean
)
LANGUAGE sql STABLE AS $$
    SELECT t.id, t.region_code, r.name, t.category, t.title,
           t.start_date, t.end_date,
           (LEAST(COALESCE(t.end_date, p_to), p_to) - GREATEST(t.start_date, p_from) + 1)::int,
           t.is_acting, t.is_concurrent
    FROM polvis.tenures t
    LEFT JOIN polvis.regions r ON r.code = t.region_code
    WHERE t.officer_id = p_officer_id
      AND t.period && daterange(p_from, p_to + 1, '[)')
    ORDER BY t.start_date;
$$;

-- ---------------------------------------------------------------------
-- 函数：空间查询 —— 点落在哪个省（PostGIS 演示）
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION polvis.fn_region_at_point(p_lon double precision, p_lat double precision)
RETURNS TABLE (code varchar(12), name text)
LANGUAGE sql STABLE AS $$
    SELECT r.code, r.name
    FROM polvis.regions r
    WHERE r.geom IS NOT NULL
      AND ST_Contains(r.geom, ST_SetSRID(ST_Point(p_lon, p_lat), 4326))
    LIMIT 1;
$$;

-- ---------------------------------------------------------------------
-- 最小权限（生产环境启用）
-- ---------------------------------------------------------------------
DO $$ BEGIN
    CREATE ROLE polvis_reader NOLOGIN;
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
    CREATE ROLE polvis_writer NOLOGIN;
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
GRANT USAGE ON SCHEMA polvis TO polvis_reader, polvis_writer;
GRANT SELECT ON ALL TABLES IN SCHEMA polvis TO polvis_reader;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA polvis TO polvis_writer;
ALTER DEFAULT PRIVILEGES IN SCHEMA polvis GRANT SELECT ON TABLES TO polvis_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA polvis GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO polvis_writer;

-- ---------------------------------------------------------------------
-- 运维提示
-- ---------------------------------------------------------------------
COMMENT ON SCHEMA polvis IS
'地方政治人事时空数据仓库。常用查询：
  SELECT * FROM polvis.fn_snapshot(DATE ''2017-10-25'', ARRAY[''110000'']);
  SELECT * FROM polvis.fn_career(1, DATE ''2012-11-08'', CURRENT_DATE);
冷启动后可执行 ANALYZE polvis.tenures; 让切片查询走 GiST 索引。';
