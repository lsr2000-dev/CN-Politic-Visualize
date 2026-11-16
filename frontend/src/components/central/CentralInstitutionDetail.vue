<script setup lang="ts">
import { computed, ref, watch } from "vue";
import LeaderRow from "@/components/panel/LeaderRow.vue";
import PartyRoleBadge from "@/components/central/PartyRoleBadge.vue";
import CentralCommitteeBadge from "@/components/central/CentralCommitteeBadge.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import { useCentralStore } from "@/stores/central";
import { useEntityPanelStore } from "@/stores/entityPanel";
import { useOfficerStore, useAppStore } from "@/stores/app";
import { useTimelineStore } from "@/stores/timeline";
import { showCentralCommittee, visiblePartyRoles, partyRankLevel } from "@/utils/partyRoles";
import type { CategoryKey, CentralLeader, Member } from "@/types";

const emit = defineEmits<{ (event: "close"): void }>();

const central = useCentralStore();
const entityPanel = useEntityPanelStore();
const officer = useOfficerStore();
const app = useAppStore();
const timeline = useTimelineStore();

const institution = computed(() => central.selectedInstitution);
const detail = computed(() => central.selectedDetail);
type InstitutionTab = "overview" | "leaders" | "roster" | "children";
const activeTab = ref<InstitutionTab>("overview");
const parentInstitution = computed(() =>
  central.org?.institutions.find((item) => item.id === institution.value?.parent_id) ?? null,
);
const childInstitutions = computed(() =>
  (central.org?.institutions ?? []).filter((item) => item.parent_id === institution.value?.id),
);
const leadershipBodyLinks = computed(() =>
  childInstitutions.value.filter((item) =>
    ["party:politburo_standing", "party:politburo"].includes(item.id),
  ),
);
function leadershipBodyMeta(body: { id: string; institution_rank: string; institution_type: string }): string {
  const rank = app.vocabulary?.ranks[body.institution_rank] ?? body.institution_rank;
  const type = body.id === "party:politburo_standing" || body.id === "party:politburo"
    ? "常设机构"
    : typeLabels.value[body.institution_type]?.label ?? body.institution_type;
  return `${rank} · ${type}`;
}
const hasRoster = computed(() => Boolean(detail.value?.committee_members?.members?.length));
const institutionTabs = computed(() => {
  const tabs: { key: InstitutionTab; label: string; count?: number }[] = [
    { key: "overview", label: "概况" },
    { key: "leaders", label: "领导班子", count: currentGroups.value.length || undefined },
  ];
  if (hasRoster.value) tabs.push({ key: "roster", label: "中央委员会名单" });
  if (childInstitutions.value.length) {
    tabs.push({ key: "children", label: "下属机构", count: childInstitutions.value.length });
  }
  return tabs;
});
watch(
  () => institution.value?.id,
  () => {
    activeTab.value = "overview";
    rosterPreviewOpen.value = false;
  },
);
watch(activeTab, (tab) => {
  if (tab !== "roster") rosterPreviewOpen.value = false;
});
function openChild(child: (typeof childInstitutions.value)[number]): void {
  void central.selectInstitution(child, timeline.currentDate);
}
function openParent(): void {
  if (parentInstitution.value) void central.selectInstitution(parentInstitution.value, timeline.currentDate);
}
const statusText = computed(() => {
  if (isNotYetCreated.value) return "尚未设立";
  if (isAbolished.value) return "已撤销";
  return "在设";
});
const overviewFacts = computed(() => [
  { label: "机构全称", value: institution.value?.name ?? "—" },
  { label: "机构简称", value: institution.value?.short_name ?? "—" },
  { label: "机构类型", value: subtitle.value || "—" },
  { label: "上级机构", value: parentInstitution.value?.name ?? "—" },
  { label: "组建时间", value: createdLabel.value || "—" },
  { label: "当前状态", value: statusText.value },
]);
const isCommitteeOrganization = computed(() => {
  const inst = institution.value;
  if (!inst) return false;
  return Boolean(
    detail.value?.committee_stats ||
    inst.group_type === "committee" ||
    inst.institution_type?.includes("committee") ||
    inst.name?.endsWith("委员会"),
  );
});
const membershipSummary = computed(() => {
  const stats = detail.value?.committee_stats;
  if (!stats) return "成员构成数据待补录";
  const alternates = stats.current_alternates ?? 0;
  const alternateReview = stats.under_investigation_alternates ?? 0;
  return `中央委员 ${stats.initial_members} · 候补委员 ${stats.initial_alternates ?? stats.elected_alternates ?? 0} · 在任 ${stats.current_members} / ${alternates} · 可出席 ${stats.actual_members} / ${alternates - alternateReview}`;
});
const leadershipComposition = computed(() => {
  const id = institution.value?.id;
  const leaders = detail.value?.leaders ?? [];
  const labels: Record<string, string> = {
    "party:politburo_standing": "中央政治局常委",
    "party:politburo": "中央政治局委员",
    "party:secretariat": "中央书记处书记",
  };
  if (!id || !labels[id] || !leaders.length) return null;
  const termStart = leaders.reduce(
    (earliest, item) => (item.start_date < earliest ? item.start_date : earliest),
    leaders[0].start_date,
  );
  const officialInitial: Record<string, number> = {
    "party:politburo_standing": 7,
    "party:politburo": 24,
    "party:secretariat": 7,
  };
  const initial = officialInitial[id] ?? leaders.filter((item) => item.start_date === termStart).length;
  const current = leaders.length;
  const added = leaders.filter((item) => item.start_date > termStart).length;
  const departed = Math.max(0, initial + added - current);
  return {
    label: labels[id],
    initial,
    departed,
    added,
    current,
    eligible: current,
    initialRemaining: current - added,
  };
});
type RosterScope = "all" | "member" | "alternate";
type RosterPhase = "all" | "initial" | "current" | "departed" | "review";
type RosterReason = "all" | "expelled" | "removed" | "resigned" | "deceased";

const rosterScope = ref<RosterScope>("all");
const rosterPhase = ref<RosterPhase>("initial");
const rosterReason = ref<RosterReason>("all");
const rosterOpen = ref(true);
const rosterPreviewOpen = ref(false);
function toggleRosterPreview(): void {
  if (!rosterPreviewOpen.value) rosterOpen.value = true;
  rosterPreviewOpen.value = !rosterPreviewOpen.value;
}
type RosterSortKey = "name" | "gender" | "ethnicity" | "birth_year" | "native_place" | "party_join_date" | "type" | "lineage" | "status";
const rosterSortKey = ref<RosterSortKey | null>(null);
const rosterSortDirection = ref<"asc" | "desc">("asc");
const chineseCollator = new Intl.Collator("zh-CN");
const scopeOptions = [
  { key: "all", label: "全部" },
  { key: "member", label: "中央委员" },
  { key: "alternate", label: "中央候补委员" },
] as const;
const phaseOptions = [
  { key: "initial", label: "初始" },
  { key: "current", label: "在任" },
  { key: "departed", label: "已离任" },
  { key: "review", label: "审查中" },
] as const;
const reasonOptions = [
  { key: "expelled", label: "被开除" },
  { key: "removed", label: "被撤职" },
  { key: "resigned", label: "辞职" },
  { key: "deceased", label: "逝世" },
] as const;
const allRosterRows = computed(() => {
  const members = detail.value?.committee_members?.members ?? [];
  const alternates = detail.value?.committee_alternates?.members ?? [];
  const unique = new Map<string, (typeof members)[number]>();
  for (const item of members) {
    unique.set(item.name.replace(/凱/g, "凯"), item);
  }
  for (const item of alternates) {
    const key = item.name.replace(/凱/g, "凯");
    const existing = unique.get(key);
    if (!existing) {
      unique.set(key, item);
    } else if (item.initial) {
      // Do not mutate the member object: the same object is also used by the
      // "中央委员" scope, where a replacement must remain non-initial.
      unique.set(key, { ...existing, initial: true });
    }
  }
  return [...unique.values()];
});
function scopeRows(scope: RosterScope) {
  if (scope === "member") return detail.value?.committee_members?.members ?? [];
  if (scope === "alternate") return detail.value?.committee_alternates?.members ?? [];
  return allRosterRows.value;
}
function phaseRows(scope: RosterScope, phase: RosterPhase) {
  const rows = scopeRows(scope);
  if (phase === "all") return rows;
  if (phase === "initial") return rows.filter((item) => item.initial);
  if (phase === "current") return rows.filter((item) => item.status === "active");
  if (phase === "review") return rows.filter((item) => item.status === "under_investigation");
  return rows.filter((item) => ["expelled", "removed", "resigned", "deceased"].includes(item.status));
}
function rosterMatches(scope: RosterScope, phase: RosterPhase, reason: RosterReason) {
  const rows = phaseRows(scope, phase);
  if (phase !== "departed" || reason === "all") return rows;
  return rows.filter((item) => item.status === reason);
}
const rosterRows = computed(() => rosterMatches(rosterScope.value, rosterPhase.value, rosterReason.value));
function filterCount(scope: RosterScope, phase: RosterPhase, reason: RosterReason) {
  return rosterMatches(scope, phase, reason).length;
}
function selectPhase(phase: RosterPhase): void {
  if (rosterPhase.value === phase) return;
  rosterPhase.value = phase;
  if (rosterPhase.value !== "departed") rosterReason.value = "all";
}
function selectScope(scope: RosterScope): void {
  rosterScope.value = scope;
  if (filterCount(scope, rosterPhase.value, rosterReason.value) === 0) {
    if (filterCount(scope, rosterPhase.value, "all") === 0) {
      rosterPhase.value = "initial";
      rosterReason.value = "all";
    } else {
      rosterReason.value = "all";
    }
  }
}
function selectReason(reason: RosterReason): void {
  rosterReason.value = rosterReason.value === reason ? "all" : reason;
}
function lineageLabel(member: { type: string; replacement?: boolean; status: string }): string {
  if (member.type === "member" && member.replacement) return "递补";
  if (member.type === "alternate" && member.status === "promoted") return "被递补";
  return "";
}
function statusLabel(member: { status: string; status_label?: string }): string {
  if (member.status === "active" || member.status === "promoted") return "";
  return member.status_label || member.status;
}
function sortValue(
  member: { name: string; gender?: string | null; ethnicity?: string | null; birth_year?: number | null; native_place?: string | null; party_join_date?: string | null; type: string; status: string; status_label?: string },
  key: RosterSortKey,
): string | number {
  if (key === "name") return member.name;
  if (key === "gender") return genderLabel(member);
  if (key === "ethnicity") return member.ethnicity ?? "汉族";
  if (key === "birth_year") return member.birth_year ?? 9999;
  if (key === "native_place") return member.native_place ?? "";
  if (key === "party_join_date") return member.party_join_date ?? "9999-99";
  if (key === "type") return member.type === "member" ? 0 : 1;
  if (key === "lineage") return lineageLabel(member);
  return statusLabel(member) || "在任";
}
function genderLabel(member: { gender?: string | null }): string {
  if (!member.gender) return "—";
  return member.gender === "F" || member.gender === "女" ? "女" : "男";
}
function partyJoinLabel(member: { party_join_date?: string | null }): string {
  return member.party_join_date ? member.party_join_date.slice(0, 7).replace("-", ".") : "—";
}
const sortedRosterRows = computed(() => {
  const key = rosterSortKey.value;
  if (!key) return rosterRows.value;
  const direction = rosterSortDirection.value === "asc" ? 1 : -1;
  return [...rosterRows.value].sort((a, b) => {
    const left = sortValue(a, key);
    const right = sortValue(b, key);
    if (typeof left === "number" && typeof right === "number") {
      return (left - right) * direction;
    }
    return chineseCollator.compare(String(left), String(right)) * direction;
  });
});
function toggleRosterSort(key: RosterSortKey): void {
  if (rosterSortKey.value === key) {
    rosterSortDirection.value = rosterSortDirection.value === "asc" ? "desc" : "asc";
    return;
  }
  rosterSortKey.value = key;
  rosterSortDirection.value = "asc";
}
function sortIndicator(key: RosterSortKey): string {
  if (rosterSortKey.value !== key) return "↕";
  return rosterSortDirection.value === "asc" ? "↑" : "↓";
}
watch(
  [() => timeline.currentDate, () => detail.value],
  () => {
    if (filterCount(rosterScope.value, rosterPhase.value, rosterReason.value) === 0) {
      rosterScope.value = "all";
      rosterPhase.value = "initial";
      rosterReason.value = "all";
    }
  },
);
const activeSeatTitles = ref<string[]>([]);
const contextId = computed(() => institution.value?.id ?? "");
const typeLabels = computed(() => app.vocabulary?.institution_types ?? {});
const partyCategoryLabels = computed(() => app.vocabulary?.party_categories ?? {});
const subtitle = computed(() => {
  if (!institution.value) return "";
  const category = institution.value.team === "party" && institution.value.party_category
    ? partyCategoryLabels.value[institution.value.party_category]
    : null;
  const label = typeLabels.value[institution.value.institution_type]?.label;
  return `${app.vocabulary?.ranks[institution.value.institution_rank] ?? institution.value.institution_rank} · ${category ?? label ?? institution.value.institution_type}`;
});

function fullTitle(title: string): string {
  if (!institution.value) return title;
  if (institution.value.id === "party:general_secretary") return institution.value.name;
  if (institution.value.id === "party:politburo_standing") return "中央政治局常委";
  if (institution.value.id === "party:politburo") return "中央政治局委员";
  if (institution.value.id === "party:secretariat") return "中央书记处书记";
  if (institution.value.id === "party:discipline") return "中央纪委书记";
  if (title.startsWith(institution.value.name)) return title;
  if (institution.value.institution_type === "state_council_leadership") {
    if (institution.value.name.endsWith(title)) return institution.value.name;
    return `${institution.value.short_name || institution.value.name}${title}`;
  }
  return `${institution.value.name}${title}`;
}
const isNotYetCreated = computed(() => institution.value?.status_at === "not_yet");
const isAbolished = computed(() => institution.value?.status_at === "abolished");
const createdLabel = computed(() =>
  (institution.value?.created_at ?? institution.value?.valid_from)?.slice(0, 7).replace("-", ".") ?? "",
);

function toMember(leader: CentralLeader, index: number): Member {
  const start = Date.parse(leader.start_date);
  const current = Date.parse(timeline.currentDate);
  const rawEnd = leader.end_date ? Date.parse(leader.end_date) : null;
  const isFuture = start > current;
  const isActive = !isFuture && (rawEnd === null || rawEnd >= current);
  const durationEnd = isFuture ? start : Math.min(rawEnd ?? current, current);
  const duration = Math.max(0, Math.floor((durationEnd - start) / 86_400_000));
  const title = fullTitle(leader.title);
  const rankLevel =
    partyRankLevel(leader.party_roles) ??
    leader.rank_override ??
    (leader.concurrent_titles?.includes("国务委员")
      ? "vice_national_leader"
      : institution.value?.institution_rank ?? "ministerial");
  return {
    tenure_id: 900000 + index,
    officer: {
      id: leader.officer_id ?? 0,
      name: leader.name,
      slug: `central-${leader.officer_id ?? leader.name}`,
      gender: null,
      birth_year: null,
    },
    title,
    category: (institution.value?.team ?? "other") as CategoryKey,
    seat_key: `central:${institution.value?.id ?? ""}:${leader.seat_type}`,
    seat_rank: 1,
    region_code: null,
    region_name: institution.value?.name ?? null,
    region_short_name: institution.value?.short_name ?? null,
    rank_level: rankLevel,
    rank_label: app.vocabulary?.ranks[rankLevel] ?? rankLevel,
    is_acting: false,
    is_concurrent: false,
    is_plural: false,
    start_date: leader.start_date,
    end_date: leader.end_date,
    start_precision: "day",
    duration_days: duration,
    is_incumbent: isActive,
    is_provisional: false,
    is_roster_snapshot: false,
    is_future: isFuture,
    status: isFuture ? "not_yet" : isActive ? "active" : "former",
    status_label: isFuture
      ? "尚未到任"
      : isActive
        ? (app.vocabulary?.tenure_status.active ?? "在任")
        : (app.vocabulary?.tenure_status.left ?? "已离任"),
    exit_reason: null,
    exit_reason_label: null,
    verified: false,
  };
}

const currentGroups = computed(() => {
  const groups = new Map<string, { member: Member; titles: string[] }>();
  const leaders = detail.value?.leaders ?? institution.value?.leaders ?? [];
  for (const [index, leader] of leaders.entries()) {
    const key = leader.officer_id ? `id:${leader.officer_id}` : `name:${leader.name}`;
    const title = fullTitle(leader.title);
    const existing = groups.get(key);
    if (existing) {
      if (!existing.titles.includes(title)) existing.titles.push(title);
      existing.member.title = existing.titles.join("、");
      if (leader.start_date < existing.member.start_date) existing.member.start_date = leader.start_date;
      if (leader.end_date === null) existing.member.end_date = null;
      continue;
    }
    groups.set(key, { member: toMember(leader, index), titles: [title] });
  }
  const rank = (title: string) =>
    title.includes("部长") ? 0 : title.includes("主任") ? 1 : title.includes("书记") ? 2 : 3;
  const ordered = [...groups.values()].sort((a, b) => rank(a.member.title) - rank(b.member.title));
  for (const group of ordered) {
    group.titles.sort((a, b) => rank(a) - rank(b));
    group.member.title = group.titles.join("、");
  }
  return ordered;
});
const historyMembers = computed(() =>
  (detail.value?.history ?? []).map((leader, index) => toMember(leader, 100 + index)),
);
const activeSeatTitle = computed(() => activeSeatTitles.value.join(" / "));
const seatHistory = computed(() =>
  historyMembers.value.filter((member) => activeSeatTitles.value.includes(member.title)),
);

watch(
  () => institution.value?.id,
  (id) => {
    activeSeatTitles.value = [];
    if (id) entityPanel.openCentral(id);
  },
  { immediate: true },
);

function openPerson(id: number | null): void {
  if (id) void officer.openOfficer(id, timeline.currentDate);
}

function openRosterPerson(member: { officer_id?: number | null }): void {
  if (member.officer_id) openPerson(member.officer_id);
}

function openSeat(group: { titles: string[] }): void {
  activeSeatTitles.value = [...group.titles];
}

function leaderFor(name: string): CentralLeader | undefined {
  return (detail.value?.leaders ?? institution.value?.leaders ?? []).find((item) => item.name === name);
}

function primaryPostFor(group: { member: Member; titles: string[] }): string {
  const leader = leaderFor(group.member.officer.name);
  if (!leader) return "";
  const own = new Set<string>([
    leader.title,
    fullTitle(leader.title),
    group.member.title,
    ...group.titles,
  ]);
  const values = [
    ...(leader.concurrent_titles ?? []),
    ...(leader.primary_post ? leader.primary_post.split(/[、，,]/) : []),
  ];
  const seen = new Set<string>();
  return values
    .map((item) => item.trim())
    .filter((item) => {
      if (!item || own.has(item) || seen.has(item)) return false;
      seen.add(item);
      return true;
    })
    .join("、");
}

function closeSeat(): void {
  activeSeatTitles.value = [];
}
</script>

<template>
  <div v-if="institution" class="flex h-full min-h-0 flex-col">
    <header class="relative shrink-0 border-b border-white/[0.07] px-5 pb-4 pt-5">
      <div class="flex items-start justify-between gap-3">
        <div class="min-w-0">
          <div class="label-eyebrow">机构信息</div>
          <h1 class="mt-1.5 truncate font-display text-[30px] leading-none tracking-wide text-paper">
            {{ institution.name }}
          </h1>
          <div class="mt-2 flex flex-wrap items-center gap-1.5">
            <span class="chip">{{ subtitle }}</span>
            <span class="chip">{{ institution.short_name }}</span>
            <span
              v-if="institution.verification_status === 'provisional'"
              class="rounded border border-amber-400/30 px-1.5 py-0.5 text-[9px] text-amber-300/90"
            >待核验</span>
          </div>
          <div v-if="institution.aliases?.length" class="mt-1.5 text-[9px] text-paper-faint">
            别名／牌子：{{ institution.aliases.join("、") }}
          </div>
        </div>
        <div class="flex shrink-0 items-center gap-1">
          <button
            v-if="parentInstitution"
            class="btn-icon"
            title="返回上级机构"
            @click="openParent"
          >
            <AppIcon name="arrow-left" :size="14" />
          </button>
          <button
            class="btn-icon"
            :class="{ 'border-vermilion/40 bg-vermilion/10 text-vermilion-bright': entityPanel.isPinned }"
            :title="entityPanel.isPinned ? '取消钉住' : '钉住以对比'"
            @click="entityPanel.togglePin"
          >
            <AppIcon name="pin" :size="14" />
          </button>
          <button class="btn-icon" title="关闭机构信息" @click="emit('close')">
            <AppIcon name="close" :size="15" />
          </button>
        </div>
      </div>
    </header>

    <nav class="institution-tabs shrink-0" aria-label="机构信息分区">
      <button
        v-for="tab in institutionTabs"
        :key="tab.key"
        class="institution-tab"
        :class="{ 'institution-tab-active': activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
        <span v-if="tab.count !== undefined" class="tabular-nums opacity-60">{{ tab.count }}</span>
      </button>
    </nav>

    <div class="institution-body min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 py-4" :class="{ 'institution-body-roster': activeTab === 'roster' }">
      <section v-if="leadershipComposition" v-show="activeTab === 'overview'" class="mb-5 rounded-xl border border-gold/20 bg-gold/[0.035] p-3">
        <div class="flex items-center justify-between">
          <div class="label-eyebrow text-gold">{{ leadershipComposition.label }}</div>
          <span class="text-[9px] text-paper-faint">截至 {{ timeline.currentDate }}</span>
        </div>
        <div class="mt-2 rounded-lg border border-white/[0.07] bg-black/10 p-3">
          <div class="space-y-0.5 text-[10px] tabular-nums text-paper-dim">
            <div class="text-[11px]">初始 <span class="font-display text-[15px] text-gold">{{ leadershipComposition.initial }}</span></div>
            <div>− 离任 <span class="text-vermilion-bright">{{ leadershipComposition.departed }}</span></div>
            <div>+ 新增 <span class="text-jade">{{ leadershipComposition.added }}</span></div>
            <div class="border-t border-white/10 pt-0.5">= 现任 <span class="text-paper">{{ leadershipComposition.current }}</span></div>
            <div>− 审查中 <span class="text-gold/80">0</span></div>
            <div class="border-t-2 border-double border-white/20 pt-1 text-paper">= 可出席 <span class="font-display text-[15px] text-gold">{{ leadershipComposition.eligible }}</span></div>
          </div>
          <div class="mt-1 text-[9px] text-paper-faint">
            初始中尚在任 {{ leadershipComposition.initialRemaining }}
          </div>
        </div>
      </section>

      <section v-if="isCommitteeOrganization" v-show="activeTab === 'overview'" class="membership-summary mb-3">
        <div class="membership-summary-label">成员构成</div>
        <div class="membership-summary-value">{{ membershipSummary }}</div>
      </section>

      <section v-if="detail?.committee_stats" v-show="activeTab === 'overview'" class="mb-5 rounded-xl border border-gold/20 bg-gold/[0.035] p-3">
        <div class="flex items-center justify-between">
          <div class="label-eyebrow text-gold">中央委员会构成 · {{ detail.committee_stats.term_label }}</div>
          <span class="text-[9px] text-paper-faint">截至 {{ timeline.currentDate }}</span>
        </div>
        <div class="mt-2 grid grid-cols-2 gap-2">
          <div class="rounded-lg border border-white/[0.07] bg-black/10 p-2">
            <div class="text-[9px] text-paper-faint">中央委员</div>
            <div class="mt-1 space-y-0.5 text-[10px] tabular-nums text-paper-dim">
              <div class="text-[11px]">初始 <span class="font-display text-[15px] text-gold">{{ detail.committee_stats.initial_members }}</span></div>
              <div>− 离任 <span class="text-vermilion-bright">{{ detail.committee_stats.departed_members }}</span></div>
              <div>+ 递补 <span class="text-jade">{{ detail.committee_stats.replacement_members }}</span></div>
              <div class="border-t border-white/10 pt-0.5">= 现任 <span class="text-paper">{{ detail.committee_stats.current_members }}</span></div>
              <div>− 审查中 <span class="text-gold/80">{{ detail.committee_stats.under_investigation }}</span></div>
              <div class="border-t-2 border-double border-white/20 pt-1 text-paper">= 可出席 <span class="font-display text-[15px] text-gold">{{ detail.committee_stats.actual_members }}</span></div>
            </div>
            <div class="mt-1 text-[9px] text-paper-faint">
              初始中尚在任 {{ detail.committee_stats.initial_members_remaining }}
            </div>
          </div>
          <div class="rounded-lg border border-white/[0.07] bg-black/10 p-2">
            <div class="text-[9px] text-paper-faint">中央候补委员</div>
            <div class="mt-1 space-y-0.5 text-[10px] tabular-nums text-paper-dim">
              <div class="text-[11px]">初始 <span class="font-display text-[15px] text-gold">{{ detail.committee_stats.initial_alternates ?? detail.committee_stats.elected_alternates }}</span></div>
              <div>− 离任 <span class="text-vermilion-bright">{{ detail.committee_stats.departed_alternates ?? 0 }}</span></div>
              <div>− 被递补 <span class="text-gold">{{ detail.committee_stats.promoted_alternates ?? 0 }}</span></div>
              <div class="border-t border-white/10 pt-0.5">= 现任 <span class="text-paper">{{ detail.committee_stats.current_alternates ?? 0 }}</span></div>
              <div>− 审查中 <span class="text-gold/80">{{ detail.committee_stats.under_investigation_alternates ?? 0 }}</span></div>
              <div class="border-t-2 border-double border-white/20 pt-1 text-paper">= 可出席 <span class="font-display text-[15px] text-gold">{{ (detail.committee_stats.current_alternates ?? 0) - (detail.committee_stats.under_investigation_alternates ?? 0) }}</span></div>
            </div>
            <div class="mt-1 text-[9px] text-paper-faint">
              初始中尚在任 {{ detail.committee_stats.initial_alternates_remaining ?? "-" }}
            </div>
          </div>
        </div>
        <div class="mt-2 space-y-1 text-[9px]">
          <div class="flex flex-wrap items-baseline gap-x-2 text-paper-dim">
            <span class="text-[10px] text-paper">中央委员</span>
            <span>可出席 {{ detail.committee_stats.actual_members }}</span>
            <span class="text-paper-faint">离任原因：开除 {{ detail.committee_stats.expelled_members }} · 辞职 {{ detail.committee_stats.resigned_members }} · 逝世 {{ detail.committee_stats.deceased_members }}</span>
            <span v-if="detail.committee_stats.under_investigation" class="text-gold/80">审查中 {{ detail.committee_stats.under_investigation }}</span>
          </div>
          <div class="flex flex-wrap items-baseline gap-x-2 text-paper-dim">
            <span class="text-[10px] text-paper">中央候补委员</span>
            <span>可出席 {{ (detail.committee_stats.current_alternates ?? 0) - (detail.committee_stats.under_investigation_alternates ?? 0) }}</span>
            <span class="text-paper-faint">离任原因：开除 {{ detail.committee_stats.alternate_expelled ?? 0 }} · 撤职 {{ detail.committee_stats.alternate_removed ?? 0 }}</span>
            <span v-if="detail.committee_stats.under_investigation_alternates" class="text-gold/80">审查中 {{ detail.committee_stats.under_investigation_alternates }}</span>
          </div>
        </div>
        <div class="mt-2 rounded-lg border border-white/[0.06] bg-white/[0.02] px-2 py-1.5 text-[9px] text-paper-faint">
          <div class="mb-1 text-[8px] tracking-[0.12em] text-paper-dim">名单收录</div>
          <div class="flex flex-wrap gap-x-3 gap-y-1">
            <span>中央委员 <span class="text-paper">{{ detail.committee_stats.member_list_collected }}</span> 人
              <span class="text-paper-faint/70">（初始 {{ detail.committee_stats.initial_members }} + 递补 {{ detail.committee_stats.replacement_members }}）</span>
            </span>
            <span>候补委员 <span class="text-paper">{{ detail.committee_stats.alternate_list_collected }}</span> / {{ detail.committee_stats.initial_alternates ?? detail.committee_stats.elected_alternates }}</span>
            <span>去重后 <span class="text-paper">{{ allRosterRows.length }}</span> 人
              <span class="text-paper-faint/70">（24 名递补人员只计一次）</span>
            </span>
          </div>
          <p class="mt-1 text-[8px] leading-relaxed text-paper-faint/70">
            名单收录只表示资料补录进度，不等于现任或可出席人数。
          </p>
        </div>
        <p class="mt-1.5 text-[8px] leading-relaxed text-paper-faint/70">
          初始人数为大会选举人数；离任包括开除、辞职、逝世；递补为中央委员递补人数，候补委员的“被递补”为转任中央委员人数。数据与名单收录情况分开显示。
        </p>
      </section>
      <section v-show="activeTab === 'overview'" class="institution-overview mb-5">
        <div class="mb-2 flex items-center justify-between">
          <div class="label-eyebrow">机构概况</div>
          <span class="text-[9px] text-paper-faint">截至 {{ timeline.currentDate }}</span>
        </div>
        <div class="grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-white/[0.07] bg-white/[0.07]">
          <div v-for="fact in overviewFacts" :key="fact.label" class="bg-ink-900/95 px-3 py-2.5">
            <div class="text-[8px] tracking-[0.12em] text-paper-faint">{{ fact.label }}</div>
            <div class="mt-1 truncate text-[11px] text-paper-dim" :title="fact.value">{{ fact.value }}</div>
          </div>
        </div>
        <p v-if="institution?.aliases?.length" class="mt-2 text-[9px] leading-relaxed text-paper-faint">
          别名／牌子：{{ institution.aliases.join("、") }}
        </p>
      </section>


      <Teleport to="body" :disabled="!rosterPreviewOpen">
        <div v-if="rosterPreviewOpen" class="roster-preview-backdrop" @click="rosterPreviewOpen = false" />
        <div v-if="detail?.committee_members?.members?.length" v-show="activeTab === 'roster'" class="roster-panel roster-fill mb-5 rounded-xl border border-white/[0.07] bg-white/[0.015]" :class="{ 'roster-preview': rosterPreviewOpen }">
        <div class="roster-title flex cursor-pointer items-center justify-between px-3 py-2 text-[10px] text-paper-dim">
          <span class="flex min-w-0 items-center gap-2">
            <span class="h-3.5 w-[2px] shrink-0 bg-vermilion" />
            <span class="truncate font-display tracking-wide text-paper">中央委员会名单 · {{ detail.committee_members.term_label }}</span>
          </span>
          <span class="flex items-center gap-2">
            <span class="tabular-nums text-paper-faint">{{ rosterRows.length }} 人</span>
            <button
              class="roster-collapse btn-ghost h-6 gap-1 px-1.5 text-[9px]"
              :title="rosterOpen ? '收起名单' : '展开名单'"
              @click.prevent.stop="rosterOpen = !rosterOpen"
            >
              <AppIcon :name="rosterOpen ? 'chevron-down' : 'chevron-right'" :size="11" />
              {{ rosterOpen ? "收起" : "展开" }}
            </button>
            <button
              class="btn-ghost h-6 gap-1 px-1.5 text-[9px]"
              :title="rosterPreviewOpen ? '关闭浮窗阅览' : '浮窗阅览'"
              @click.prevent.stop="toggleRosterPreview"
            >
              <AppIcon :name="rosterPreviewOpen ? 'close' : 'float'" :size="11" />
              {{ rosterPreviewOpen ? "关闭浮窗" : "浮窗阅览" }}
            </button>
          </span>
        </div>
        <template v-if="rosterOpen">
        <div class="roster-controls space-y-1 border-t border-white/[0.06] px-3 pb-2 pt-2">
          <div class="roster-filter-hint">
            <div class="roster-filter-hint-title">筛选说明</div>
            <p>一级、二级为必选，结果取交集。</p>
            <p>三级仅在“已离任”时出现，可选。</p>
          </div>
          <div class="roster-filter-label">一级 · 名单范围 <span>必选</span></div>
          <div class="flex flex-wrap gap-1">
            <button
              v-for="option in scopeOptions"
              :key="option.key"
              class="inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[9px] transition disabled:cursor-not-allowed disabled:opacity-40"
              :class="rosterScope === option.key
                ? 'border-gold/50 bg-gold/10 text-gold'
                : 'border-white/10 text-paper-faint hover:border-white/25 hover:text-paper'"
              :disabled="filterCount(option.key, rosterPhase, rosterReason) === 0"
              @click="selectScope(option.key)"
            >
              {{ option.label }}
              <span class="tabular-nums opacity-70">{{ filterCount(option.key, rosterPhase, rosterReason) }}</span>
            </button>
          </div>
          <div class="roster-filter-label">二级 · 身份阶段 <span>必选</span></div>
          <div class="flex flex-wrap gap-1">
            <button
              v-for="option in phaseOptions"
              :key="option.key"
              class="inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[9px] transition disabled:cursor-not-allowed disabled:opacity-40"
              :class="rosterPhase === option.key
                ? 'border-gold/50 bg-gold/10 text-gold'
                : 'border-white/10 text-paper-faint hover:border-white/25 hover:text-paper'"
              :disabled="filterCount(rosterScope, option.key, 'all') === 0"
              @click="selectPhase(option.key)"
            >
              {{ option.label }}
              <span class="tabular-nums opacity-70">{{ filterCount(rosterScope, option.key, 'all') }}</span>
            </button>
          </div>
          <div v-if="rosterPhase === 'departed'" class="border-t border-white/[0.05] pt-1">
            <div class="roster-filter-label">三级 · 离任原因 <span>可选</span></div>
            <div class="flex flex-wrap gap-1">
            <button
              v-for="option in reasonOptions"
              :key="option.key"
              class="inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[9px] transition disabled:cursor-not-allowed disabled:opacity-40"
              :class="rosterReason === option.key
                ? 'border-vermilion/45 bg-vermilion/10 text-vermilion-bright'
                : 'border-white/10 text-paper-faint hover:border-white/25 hover:text-paper'"
              :disabled="filterCount(rosterScope, 'departed', option.key) === 0"
              @click="selectReason(option.key)"
            >
              {{ option.label }}
              <span class="tabular-nums opacity-70">{{ filterCount(rosterScope, 'departed', option.key) }}</span>
            </button>
            </div>
          </div>
        </div>
        <div class="roster-table px-3">
          <div class="roster-table-inner">
          <template v-if="rosterPreviewOpen">
          <div class="roster-head grid grid-cols-[76px_34px_42px_48px_minmax(0,1fr)_68px_40px_42px_52px] items-baseline gap-2 border-b border-white/[0.08] pb-1 pr-1.5 text-[8px] text-paper-faint">
            <button class="flex items-center gap-0.5 text-left hover:text-gold" @click="toggleRosterSort('name')">姓名<span class="opacity-60">{{ sortIndicator("name") }}</span></button>
            <button class="flex items-center gap-0.5 text-left hover:text-gold" @click="toggleRosterSort('gender')">性别<span class="opacity-60">{{ sortIndicator("gender") }}</span></button>
            <button class="flex items-center gap-0.5 text-left hover:text-gold" @click="toggleRosterSort('ethnicity')">民族<span class="opacity-60">{{ sortIndicator("ethnicity") }}</span></button>
            <button class="flex items-center gap-0.5 text-left hover:text-gold" @click="toggleRosterSort('birth_year')">出生年<span class="opacity-60">{{ sortIndicator("birth_year") }}</span></button>
            <button class="flex items-center gap-0.5 text-left hover:text-gold" @click="toggleRosterSort('native_place')">籍贯<span class="opacity-60">{{ sortIndicator("native_place") }}</span></button>
            <button class="flex items-center gap-0.5 text-left hover:text-gold" @click="toggleRosterSort('party_join_date')">入党时间<span class="opacity-60">{{ sortIndicator("party_join_date") }}</span></button>
            <button class="justify-self-end hover:text-gold" @click="toggleRosterSort('type')">身份<span class="opacity-60">{{ sortIndicator("type") }}</span></button>
            <button class="justify-self-end text-right hover:text-gold" @click="toggleRosterSort('lineage')">递补<span class="opacity-60">{{ sortIndicator("lineage") }}</span></button>
            <button class="justify-self-end text-right hover:text-gold" @click="toggleRosterSort('status')">状态<span class="opacity-60">{{ sortIndicator("status") }}</span></button>
          </div>
          <div class="roster-scroll max-h-64 overflow-y-auto">
            <div class="py-2">
              <div
                v-for="member in sortedRosterRows"
                :key="member.type + member.name"
                class="grid grid-cols-[76px_34px_42px_48px_minmax(0,1fr)_68px_40px_42px_52px] items-baseline gap-2 border-b border-white/[0.04] py-1 last:border-b-0"
              >
                <button
                  class="roster-name truncate text-left text-[10px] text-paper underline decoration-white/20 decoration-dotted underline-offset-2 transition hover:text-gold hover:decoration-gold/60"
                  :title="`查看 ${member.name} 官员资料`"
                  @click="openRosterPerson(member)"
                >{{ member.name }}</button>
                <span class="truncate text-[9px] text-paper-faint">{{ genderLabel(member) }}</span>
                <span class="truncate text-[9px] text-paper-faint" :title="member.ethnicity ?? '民族待核验'">{{ member.ethnicity ?? "—" }}</span>
                <span class="truncate text-[9px] tabular-nums text-paper-faint">{{ member.birth_year ?? "待核验" }}</span>
                <span class="min-w-0 truncate text-[9px] text-paper-faint" :title="member.native_place ?? '籍贯待核验'">{{ member.native_place ?? "待核验" }}</span>
                <span class="truncate text-[9px] tabular-nums text-paper-faint">{{ partyJoinLabel(member) }}</span>
                <span
                  class="justify-self-end rounded border px-1 py-px text-[8px]"
                  :class="member.type === 'alternate'
                    ? 'border-jade/35 text-jade'
                    : 'border-white/10 text-paper-faint'"
                >{{ member.type === "alternate" ? "候补" : "委员" }}</span>
                <span class="justify-self-end whitespace-nowrap text-[8px] text-gold/80">{{ lineageLabel(member) }}</span>
                <span class="justify-self-end whitespace-nowrap text-right text-[8px] text-vermilion-bright">{{ statusLabel(member) }}</span>
              </div>
              <p v-if="!rosterRows.length" class="py-2 text-center text-[9px] text-paper-faint">该筛选下暂无记录。</p>
            </div>
          </div>
          </template>
          <template v-else>
            <div class="roster-head grid grid-cols-[76px_56px_minmax(0,1fr)_82px_56px] items-baseline gap-2 border-b border-white/[0.08] pb-1 pr-1.5 text-[8px] text-paper-faint">
              <button class="flex items-center gap-0.5 text-left hover:text-gold" @click="toggleRosterSort('name')">姓名<span class="opacity-60">{{ sortIndicator("name") }}</span></button>
              <button class="flex items-center gap-0.5 text-left hover:text-gold" @click="toggleRosterSort('birth_year')">出生年<span class="opacity-60">{{ sortIndicator("birth_year") }}</span></button>
              <button class="flex items-center gap-0.5 text-left hover:text-gold" @click="toggleRosterSort('native_place')">籍贯<span class="opacity-60">{{ sortIndicator("native_place") }}</span></button>
              <button class="justify-self-start text-left hover:text-gold" @click="toggleRosterSort('type')">身份<span class="opacity-60">{{ sortIndicator("type") }}</span></button>
              <button class="justify-self-end text-right hover:text-gold" @click="toggleRosterSort('status')">状态<span class="opacity-60">{{ sortIndicator("status") }}</span></button>
            </div>
            <div class="roster-scroll max-h-64 overflow-y-auto">
              <div class="py-2">
                <div
                  v-for="member in sortedRosterRows"
                  :key="member.type + member.name"
                  class="grid grid-cols-[76px_56px_minmax(0,1fr)_82px_56px] items-baseline gap-2 border-b border-white/[0.04] py-1 last:border-b-0"
                >
                  <button
                    class="truncate text-left text-[11px] text-paper underline decoration-white/20 decoration-dotted underline-offset-2 transition hover:text-gold hover:decoration-gold/60"
                    :title="`查看 ${member.name} 官员资料`"
                    @click="openRosterPerson(member)"
                  >{{ member.name }}</button>
                  <span class="truncate text-[9px] tabular-nums text-paper-faint">{{ member.birth_year ?? "待核验" }}</span>
                  <span class="min-w-0 truncate text-[9px] text-paper-faint" :title="member.native_place ?? '籍贯待核验'">{{ member.native_place ?? "待核验" }}</span>
                  <span class="flex items-center justify-start gap-1">
                    <span
                      class="rounded border px-1 py-px text-[8px]"
                      :class="member.type === 'alternate'
                        ? 'border-jade/35 text-jade'
                        : 'border-white/10 text-paper-faint'"
                    >{{ member.type === "alternate" ? "候补" : "委员" }}</span>
                    <span v-if="lineageLabel(member)" class="whitespace-nowrap text-[8px] text-gold/80">{{ lineageLabel(member) }}</span>
                  </span>
                  <span class="justify-self-end whitespace-nowrap text-right text-[8px] text-vermilion-bright">{{ statusLabel(member) }}</span>
                </div>
                <p v-if="!rosterRows.length" class="py-2 text-center text-[9px] text-paper-faint">该筛选下暂无记录。</p>
              </div>
            </div>
          </template>
        </div>
        </div>
        </template>
        </div>
      </Teleport>

      <section v-show="activeTab === 'leaders'">
        <div v-if="leadershipBodyLinks.length" class="mb-4">
          <div class="label-eyebrow mb-2">领导机构</div>
          <div class="grid gap-2 sm:grid-cols-2">
            <button
              v-for="body in leadershipBodyLinks"
              :key="body.id"
              class="rounded-lg border border-white/[0.07] bg-white/[0.02] px-3 py-2.5 text-left transition hover:border-gold/30 hover:bg-gold/[0.04]"
              @click="openChild(body)"
            >
              <div class="flex items-center justify-between gap-2">
                <span class="truncate text-[11px] text-paper">{{ body.name }}</span>
                <AppIcon name="chevron-right" :size="11" class="shrink-0 text-paper-faint" />
              </div>
              <div class="mt-1 truncate text-[9px] text-paper-faint">
                {{ leadershipBodyMeta(body) }}
              </div>
            </button>
          </div>
        </div>
        <div class="label-eyebrow mb-2">现任正职</div>
        <div v-if="currentGroups.length" class="space-y-2">
          <div v-for="group in currentGroups" :key="group.member.seat_key + group.member.start_date" class="entity-member">
            <LeaderRow
              :member="group.member"
              lead
              @select="openPerson(group.member.officer.id)"
              @history="openSeat(group)"
            />
            <div class="mt-1 flex flex-wrap items-center gap-1.5 pl-12">
              <PartyRoleBadge :roles="visiblePartyRoles(leaderFor(group.member.officer.name)?.party_roles, contextId)" />
              <CentralCommitteeBadge
                v-if="showCentralCommittee(leaderFor(group.member.officer.name)?.party_roles, contextId)"
                :committee="leaderFor(group.member.officer.name)?.central_committee ?? null"
              />
            </div>
            <p
              v-if="primaryPostFor(group)"
              class="mt-1 pl-12 text-[9px] leading-snug text-paper-faint"
            >
              主要兼任：{{ primaryPostFor(group) }}
            </p>
            <p
              v-if="leaderFor(group.member.officer.name)?.birth_year || leaderFor(group.member.officer.name)?.native_place"
              class="mt-1 pl-12 text-[9px] leading-snug text-paper-faint/80"
            >
              出生：{{ leaderFor(group.member.officer.name)?.birth_year ?? "待考" }}
              · 籍贯：{{ leaderFor(group.member.officer.name)?.native_place ?? "待考" }}
            </p>
          </div>
        </div>
        <p v-else-if="isNotYetCreated" class="text-[10px] text-paper-faint">
          {{ institution?.created_at ? `该机构于 ${createdLabel} 组建，当前时点尚未设立。` : `该机构历史数据自 ${createdLabel} 起收录。` }}
        </p>
        <p v-else-if="isAbolished" class="text-[10px] text-paper-faint">该机构已撤销。</p>
        <p v-else-if="institution?.id === 'party:central_committee'" class="text-[10px] leading-relaxed text-paper-faint">
          中央委员会由党的全国代表大会选举产生，是集体领导机构；中央委员会总书记单列。
        </p>
        <p v-else class="text-[10px] text-paper-faint">该机构正职信息待补录。</p>
      </section>

      <section v-if="activeSeatTitle" v-show="activeTab === 'leaders'" class="mt-5 border-t border-white/10 pt-3">
        <button class="mb-2 inline-flex items-center gap-1 text-[9px] text-paper-faint hover:text-paper" @click="closeSeat">
          <AppIcon name="arrow-left" :size="10" /> 返回机构
        </button>
        <div class="flex items-center justify-between">
          <div class="label-eyebrow">历任 · {{ activeSeatTitle }}</div>
          <span class="text-[9px] text-paper-faint">{{ seatHistory.length }} 段</span>
        </div>
        <div v-if="seatHistory.length" class="mt-2 space-y-1">
          <div
            v-for="member in seatHistory"
            :key="member.seat_key + member.start_date + member.officer.name"
            :class="member.is_future ? 'central-history-future' : ''"
          >
            <LeaderRow
              :member="member"
              @select="openPerson(member.officer.id)"
              @history="() => undefined"
            />
          </div>
        </div>
        <p v-else class="mt-2 text-[10px] text-paper-faint">该岗位暂无历任记录。</p>
      </section>

      <p v-else v-show="activeTab === 'leaders'" class="mt-4 flex items-start gap-1.5 text-[9px] leading-relaxed text-paper-faint/65">
        <AppIcon name="info" :size="10" class="mt-px shrink-0" />
        这是机构页面；点击官员进入官员档案。点击任一正职的“历任”查看该岗位的历任领导。
      </p>

      <section v-show="activeTab === 'children'" class="mt-1">
        <div class="mb-2 flex items-center justify-between">
          <div class="label-eyebrow">下属机构</div>
          <span class="text-[9px] text-paper-faint">{{ childInstitutions.length }} 个</span>
        </div>
        <div class="grid gap-2 sm:grid-cols-2">
          <button
            v-for="child in childInstitutions"
            :key="child.id"
            class="rounded-lg border border-white/[0.07] bg-white/[0.02] px-3 py-2.5 text-left transition hover:border-gold/30 hover:bg-gold/[0.04]"
            @click="openChild(child)"
          >
            <div class="truncate text-[11px] text-paper">{{ child.name }}</div>
            <div class="mt-1 truncate text-[9px] text-paper-faint">
              {{ app.vocabulary?.ranks[child.institution_rank] ?? child.institution_rank }}
              · {{ typeLabels[child.institution_type]?.label ?? child.institution_type }}
            </div>
          </button>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.institution-tabs {
  display: flex;
  flex: 0 0 auto;
  gap: 4px;
  overflow-x: auto;
  border-bottom: 1px solid rgba(255, 255, 255, 0.07);
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.012);
}
.institution-tab {
  flex: 0 0 auto;
  border: 1px solid transparent;
  border-radius: 5px;
  padding: 4px 8px;
  font-size: 10px;
  color: rgba(232, 224, 205, 0.52);
  transition: color 0.15s ease, border-color 0.15s ease, background 0.15s ease;
}
.institution-tab:hover {
  border-color: rgba(255, 255, 255, 0.12);
  color: #e8e0cd;
}
.institution-tab-active {
  border-color: rgba(176, 138, 74, 0.45);
  background: rgba(176, 138, 74, 0.1);
  color: #d8b878;
}
.membership-summary {
  display: flex;
  align-items: baseline;
  gap: 10px;
  border: 1px solid rgba(176, 138, 74, 0.22);
  border-radius: 7px;
  background: rgba(176, 138, 74, 0.055);
  padding: 8px 10px;
}
.membership-summary-label {
  flex: 0 0 auto;
  color: #d8b878;
  font-size: 9px;
  letter-spacing: 0.12em;
}
.membership-summary-value {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #b9b09c;
  font-size: 9px;
  font-variant-numeric: tabular-nums;
}
.institution-body-roster {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.institution-body-roster .roster-fill {
  display: flex;
  flex: 1;
  min-height: 0;
  flex-direction: column;
  margin-bottom: 0;
}
.institution-body-roster .roster-fill > .roster-title,
.institution-body-roster .roster-fill > .roster-controls {
  flex: 0 0 auto;
}
.institution-body-roster .roster-fill .roster-table {
  display: flex;
  flex: 1;
  min-height: 0;
  flex-direction: column;
}
.institution-body-roster .roster-fill .roster-table-inner {
  display: flex;
  flex: 1;
  min-height: 0;
  flex-direction: column;
}
.institution-body-roster .roster-fill .roster-scroll {
  max-height: none !important;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.22) transparent;
}
.institution-body-roster .roster-fill .roster-scroll::-webkit-scrollbar {
  display: block;
  width: 6px;
  height: 6px;
}
.institution-body-roster .roster-fill .roster-scroll::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.22);
}
.institution-body-roster .roster-fill .roster-scroll::-webkit-scrollbar-track {
  background: transparent;
}
.institution-body-roster .roster-fill .roster-head {
  padding-right: 10px;
}
.entity-member + .entity-member {
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  padding-top: 6px;
}
.central-history-future {
  border: 1px dashed rgba(255, 255, 255, 0.12);
  border-radius: 8px;
  opacity: 0.62;
}
.central-history-future:hover {
  opacity: 1;
}
.roster-preview-backdrop {
  position: fixed;
  inset: 0;
  z-index: 85;
  background: rgba(5, 8, 12, 0.68);
  backdrop-filter: blur(3px);
}
.roster-preview {
  position: fixed;
  left: 50%;
  top: 5vh;
  z-index: 90;
  display: grid;
  grid-template-columns: 248px minmax(0, 1fr);
  grid-template-rows: auto minmax(0, 1fr);
  width: min(1280px, 92vw);
  height: min(86vh, 920px);
  max-height: 86vh;
  margin: 0 !important;
  overflow: hidden;
  transform: translateX(-50%);
  background: rgb(13 17 23) !important;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.55);
}
.roster-preview > .roster-title {
  grid-column: 1 / -1;
  grid-row: 1;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.02);
}
.roster-preview > .roster-controls {
  grid-column: 1;
  grid-row: 2;
  min-height: 0;
  height: 100%;
  overflow-y: auto;
  border-top: 0;
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  padding: 14px 12px;
}
.roster-preview > .roster-table {
  grid-column: 2;
  grid-row: 2;
  display: flex;
  width: 100%;
  min-width: 0;
  min-height: 0;
  height: 100%;
  flex-direction: column;
  overflow: hidden;
  padding: 14px 20px 18px;
}
.roster-preview .roster-table-inner {
  display: flex;
  width: min(960px, 100%);
  min-height: 0;
  flex: 1;
  flex-direction: column;
  margin: 0 auto;
}
.roster-preview .roster-scroll {
  max-height: none !important;
  min-height: 0;
  flex: 1;
}
.roster-preview .roster-controls > div {
  align-items: stretch;
  flex-direction: column;
  gap: 4px;
}
.roster-preview .roster-controls button {
  width: 100%;
  justify-content: space-between;
  text-align: left;
}
.roster-preview .roster-collapse {
  display: none;
}
.roster-preview > .roster-title {
  font-size: 17px;
  padding: 16px 20px;
  background:
    linear-gradient(90deg, rgba(200, 73, 47, 0.08), transparent 36%),
    rgba(255, 255, 255, 0.02);
}
.roster-preview > .roster-title .font-display {
  font-size: 18px;
  letter-spacing: 0.035em;
  color: #e8e0cd;
}
.roster-filter-hint {
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.025);
  padding: 7px 8px;
  color: #8e8778;
  font-size: 8px;
  line-height: 1.6;
}
.roster-filter-hint-title {
  color: #b9b09c;
  font-size: 8px;
  letter-spacing: 0.08em;
  margin-bottom: 2px;
}
.roster-filter-hint p {
  margin: 0;
}
.roster-panel:not(.roster-preview) .roster-filter-hint {
  display: none;
}
.roster-filter-label {
  color: #b9b09c;
  font-size: 8px;
  letter-spacing: 0.08em;
  margin-top: 7px;
  margin-bottom: 2px;
}
.roster-filter-label span {
  color: #a8834a;
  font-size: 7px;
  margin-left: 4px;
}
.roster-preview .roster-filter-hint {
  font-size: 10px;
  line-height: 1.7;
  padding: 10px;
}
.roster-preview .roster-filter-hint-title {
  font-size: 10px;
  margin-bottom: 4px;
}
.roster-preview .roster-filter-label {
  font-size: 10px;
  margin-top: 12px;
}
.roster-preview .roster-name {
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.01em;
}
.roster-preview .roster-table {
  font-variant-numeric: tabular-nums;
}
.roster-preview .roster-controls button {
  font-size: 10px;
  padding-top: 5px;
  padding-bottom: 5px;
}
.roster-preview .roster-table .grid > span {
  font-size: 10px;
}
.roster-preview .roster-table .grid {
  padding-top: 6px;
  padding-bottom: 6px;
}
.roster-preview .roster-head button {
  font-size: 9px;
}
@media (max-width: 760px) {
  .roster-preview {
    top: 0;
    width: 100vw;
    height: 100dvh;
    max-height: 100dvh;
    grid-template-columns: 1fr;
    grid-template-rows: auto auto minmax(0, 1fr);
    border-radius: 0;
  }
  .roster-preview > .roster-controls {
    grid-column: 1;
    grid-row: 2;
    height: auto;
    max-height: 30vh;
    border-right: 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  }
  .roster-preview > .roster-table {
    grid-column: 1;
    grid-row: 3;
    height: auto;
    padding: 12px;
  }
  .roster-preview .roster-controls > div {
    flex-direction: row;
    flex-wrap: wrap;
  }
  .roster-preview .roster-controls button {
    width: auto;
  }
}
</style>
