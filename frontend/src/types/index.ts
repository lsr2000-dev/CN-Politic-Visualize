export type CategoryKey = "party" | "congress" | "government" | "cppcc" | "other";

export type ViewMode = "sidebar" | "floating" | "fullscreen";

export interface Coverage {
  dataset_id: string;
  coverage_start: string;
  coverage_end: string;
  beyond_coverage: boolean;
  status: string;
  disclaimer: string | null;
}

export interface OfficerBrief {
  id: number;
  name: string;
  slug: string;
  gender: string | null;
  birth_year: number | null;
}

export interface Member {
  tenure_id: number;
  officer: OfficerBrief;
  title: string;
  category: CategoryKey;
  seat_key: string;
  position_uid?: string;
  seat_rank: number;
  region_code: string | null;
  region_name: string | null;
  region_short_name: string | null;
  rank_level: string;
  rank_label: string;
  is_acting: boolean;
  is_concurrent: boolean;
  is_plural: boolean;
  start_date: string;
  end_date: string | null;
  start_precision: string;
  duration_days: number;
  is_incumbent: boolean;
  is_provisional: boolean;
  is_roster_snapshot: boolean;
  status: string;
  status_label: string;
  exit_reason: string | null;
  exit_reason_label: string | null;
  verified: boolean;
}

export interface Team {
  key: CategoryKey;
  label: string;
  members: Member[];
}

export interface Teams {
  party: Team;
  congress: Team;
  government: Team;
  cppcc: Team;
}

export interface RegionMetrics {
  party_days: number;
  governor_days: number;
  party_count: number;
  governor_count: number;
  filled: number;
  acting: number;
}

export interface RegionSnapshot {
  region_code: string;
  region_name: string;
  short_name: string;
  level: string;
  centroid: [number, number] | null;
  teams: Teams;
  headline: Record<"party" | "government" | "congress" | "cppcc", Member | null>;
  filled: number;
  member_count: number;
  acting_count: number;
  metrics: RegionMetrics;
}

export interface SnapshotStats {
  region_count: number;
  member_count: number;
  acting_count: number;
  regions_with_gaps: number;
}

export interface SnapshotResponse {
  as_of: string;
  coverage: Coverage;
  stats: SnapshotStats;
  regions: RegionSnapshot[];
}

export interface RegionDetailResponse {
  as_of: string;
  coverage: Coverage;
  region: RegionSnapshot;
}

export interface RegionOut {
  code: string;
  name: string;
  short_name: string;
  level: string;
  parent_code: string | null;
  centroid: [number, number] | null;
  sort_order: number;
}

export interface SeatSpan extends Member {
  officer_name: string;
  officer_id: number;
  gap_before_days: number | null;
  is_current: boolean;
  is_future: boolean;
  event_type: string | null;
  event_label: string | null;
  event_date: string | null;
}

export interface RegionTimelineSpan extends Member {
  officer_name: string;
  officer_id: number;
}

export interface RegionTimelineLane {
  key: string;
  category: CategoryKey;
  title: string;
  label: string;
  rank: number;
  spans: RegionTimelineSpan[];
}

export interface RegionTimelineResponse {
  region_code: string;
  region_name: string;
  from: string;
  to: string;
  lanes: RegionTimelineLane[];
}

export interface SeatHistoryResponse {
  region_code: string;
  region_name: string;
  seat_key: string;
  title: string;
  category: CategoryKey;
  as_of: string;
  spans: SeatSpan[];
  holder_count: number;
  acting_count: number;
  incumbent: Member | null;
}

export interface Officer {
  id: number;
  slug: string;
  name: string;
  gender: string | null;
  birth_year: number | null;
  native_place: string | null;
  ethnicity: string | null;
  party_join_date: string | null;
  work_start_date: string | null;
  education: string | null;
  degree: string | null;
  school: string | null;
  bio: string | null;
  portrait_url: string | null;
  is_deceased: boolean;
}

export interface OfficerEvent {
  id: number;
  event_type: string;
  event_date: string;
  title: string;
  description: string | null;
  source_url: string | null;
  source_title: string | null;
  verified: boolean;
}

export interface OfficerProfileResponse {
  officer: Officer;
  current: Member[];
  previous: Member | null;
  next: Member | null;
  events: OfficerEvent[];
  status: string;
  status_label: string;
  stats: {
    position_count: number;
    province_count: number;
    acting_count: number;
    first_start: string | null;
    latest_end: string | null;
  };
  as_of: string;
  coverage: Coverage;
}

export interface CareerSpan extends Member {
  lane_key: string;
  officer_name: string;
  officer_id: number;
  org_name: string | null;
  clipped_start: string;
}

export interface CareerLane {
  key: string;
  label: string;
  full_label: string;
  order: number;
  spans: CareerSpan[];
}

export interface CareerResponse {
  officer: Officer;
  range: {
    from: string;
    to: string;
    coverage_end: string;
    requested_to: string | null;
  };
  lanes: CareerLane[];
  events: OfficerEvent[];
  context: {
    previous: Member | null;
    next: Member | null;
    status: string;
    status_label: string;
  } | null;
  summary: {
    span_count: number;
    province_count: number;
    acting_count: number;
    total_days: number;
  };
  coverage: Coverage;
}

export interface CategoryInfo {
  key: CategoryKey;
  label: string;
  order: number;
  accent: string;
}

export interface MetricInfo {
  key: MetricKey;
  label: string;
  unit: string;
  kind: "continuous" | "discrete";
}

export interface EventInfo {
  date: string;
  type: string;
  label: string;
  description: string;
}

export interface DatasetInfo {
  id: string;
  coverage_start: string;
  coverage_end: string;
  plenum_date: string | null;
  status: string;
  disclaimer: string | null;
  counts: Record<string, number>;
}

export interface MetaResponse {
  dataset: DatasetInfo;
  categories: CategoryInfo[];
  metrics: MetricInfo[];
  events: EventInfo[];
  geo: { geojson: string; adcode_property: string; name_property: string };
  timezone: string;
  generated_at: string;
}

export interface CompareResponse {
  as_of: string;
  coverage: Coverage;
  regions: RegionSnapshot[];
}

export interface DirectoryItem {
  officer_id: number;
  name: string;
  gender: string | null;
  birth_year: number | null;
  native_place: string | null;
  current_title: string | null;
  region_code: string | null;
  region_name: string | null;
  category: CategoryKey | null;
  rank_level: string;
  rank_label: string;
  start_date: string | null;
  end_date: string | null;
  start_precision: string | null;
  status: string;
  status_label: string;
  status_date: string | null;
  status_title: string | null;
  previous_title: string | null;
  previous_rank_label: string | null;
  next_title: string | null;
  next_rank_label: string | null;
  central_committee: CentralCommittee | null;
  party_roles: CentralPartyRole[];
  source_count: number;
  verified: boolean;
  updated_at: string;
}

export interface CoverageCategory {
  provinces: number;
  total: number;
  ratio: number;
}

export interface CoverageRegion {
  region_code: string;
  region_name: string;
  short_name: string;
  filled: number;
  principal_complete: boolean;
  categories: Record<string, boolean>;
  member_count: number;
  roster_snapshots: number;
}

export interface CoverageCheckpoint {
  date: string;
  provinces_complete: number;
  principal_coverage: number;
}

export interface CoverageVacancy {
  region_code: string;
  region_name: string;
  category: CategoryKey;
  reason: string;
  date: string;
}

export interface CoverageResponse {
  as_of: string;
  dataset_version: string;
  plenum_date: string;
  provinces_total: number;
  provinces_complete: number;
  provinces_accounted: number;
  principal_coverage: number;
  checkpoints: CoverageCheckpoint[];
  vacancies: CoverageVacancy[];
  category_coverage: Record<string, CoverageCategory>;
  principal_slots: number;
  principal_slots_filled: number;
  tenures: number;
  officers: number;
  events: number;
  verified_tenures: number;
  verified_ratio: number;
  roster_snapshots: number;
  regions: CoverageRegion[];
}

export interface DirectoryResponse {
  items: DirectoryItem[];
  total: number;
  page: number;
  page_size: number;
  as_of: string;
  dataset_version: string;
  coverage: CoverageResponse;
  updated_at: string;
}

export type MetricKey =
  | "party_days"
  | "governor_days"
  | "party_count"
  | "governor_count"
  | "filled";

export interface GeoFeatureProperties {
  adcode: number;
  name: string;
  center: [number, number];
  centroid: [number, number];
  level: string;
}

export interface GeoJson {
  type: "FeatureCollection";
  features: Array<{
    type: "Feature";
    properties: GeoFeatureProperties;
    geometry: unknown;
  }>;
}

export interface CentralCommittee {
  term: number;
  term_label: string;
  type: "member" | "alternate";
  status: "active" | "expelled" | "retired" | "deceased" | "resigned" | "term_ended";
  label: string;
  status_label: string;
  status_note?: string;
}

export interface CentralPartyRole {
  term: number;
  term_label: string;
  role: "politburo_standing" | "politburo_member" | "secretariat_member";
  label: string;
  status: "active" | "expelled" | "retired" | "deceased" | "term_ended";
}

export interface CentralLeader {
  name: string;
  title: string;
  seat_id?: string;
  position_uid?: string;
  start_date: string;
  end_date: string | null;
  seat_type: string;
  central_committee: CentralCommittee | null;
  party_roles: CentralPartyRole[];
  primary_post: string | null;
  officer_id: number | null;
  birth_year?: number | null;
  native_place?: string | null;
  rank_override?: string | null;
  concurrent_titles?: string[];
}

export interface CentralInstitution {
  id: string;
  parent_id: string | null;
  team: "party" | "congress" | "government" | "cppcc" | "other";
  group_type: string;
  institution_type: string;
  name: string;
  short_name: string;
  institution_rank: string;
  level: number;
  sort_order: number;
  created_at?: string | null;
  valid_from?: string | null;
  valid_to?: string | null;
  status?: string;
  status_at?: string;
  party_category?: string | null;
  aliases?: string[];
  verification_status?: "verified" | "provisional" | "unverified";
  leaders: CentralLeader[];
  leader: CentralLeader | null;
}

export interface CentralTeamSummary {
  key: string;
  label: string;
  short: string;
  color: string;
  count: number;
  leader: CentralLeader | null;
}

export interface CentralOverview {
  as_of: string;
  coverage_start: string;
  team_coverage?: Record<string, { start: string; end: string; status: string }>;
  teams: Record<string, CentralTeamSummary>;
  other: Array<{ key: string; label: string; count: number; color: string }>;
  coverage: { required: number; filled: number; missing: number; ratio: number };
}

export interface CentralOrgResponse {
  team: string;
  as_of: string;
  institutions: CentralInstitution[];
}

export interface CentralCommitteeResponse {
  name: string;
  as_of: string;
  committee: CentralCommittee | null;
  party_roles: CentralPartyRole[];
}

export interface CentralInstitutionDetail extends CentralInstitution {
  history: CentralLeader[];
}
