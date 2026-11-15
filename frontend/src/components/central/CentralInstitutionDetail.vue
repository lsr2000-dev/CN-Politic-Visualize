<script setup lang="ts">
import { computed, ref, watch } from "vue";
import LeaderRow from "@/components/panel/LeaderRow.vue";
import PartyRoleBadge from "@/components/central/PartyRoleBadge.vue";
import CentralCommitteeBadge from "@/components/central/CentralCommitteeBadge.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import { useCentralStore } from "@/stores/central";
import { useEntityPanelStore } from "@/stores/entityPanel";
import { useOfficerStore } from "@/stores/app";
import { useTimelineStore } from "@/stores/timeline";
import { showCentralCommittee, visiblePartyRoles, partyRankLevel } from "@/utils/partyRoles";
import type { CategoryKey, CentralLeader, Member } from "@/types";

const emit = defineEmits<{ (event: "close"): void }>();

const central = useCentralStore();
const entityPanel = useEntityPanelStore();
const officer = useOfficerStore();
const timeline = useTimelineStore();

const institution = computed(() => central.selectedInstitution);
const detail = computed(() => central.selectedDetail);
const activeSeatTitles = ref<string[]>([]);
const contextId = computed(() => institution.value?.id ?? "");
const rankLabels: Record<string, string> = {
  national_leader: "正国级",
  vice_national_leader: "副国级",
  ministerial: "正部级",
  vice_ministerial: "副部级",
  departmental: "正地厅级",
  bureau: "局级",
};
const typeLabels: Record<string, string> = {
  ministry: "国务院组成部门",
  ministry_group: "国务院组成部门",
  agency: "国务院直属机构",
  agency_group: "国务院直属机构",
  service: "国务院办事机构",
  institution: "国务院直属事业单位",
  special: "国务院特设机构",
  commission: "专门委员会",
  group: "机构分组",
  state_council_leadership: "国务院领导",
  admin_bureau: "部委管理的国家局",
  outpost: "国务院派出机构",
};
const partyCategoryLabels: Record<string, string> = {
  leadership: "中央领导机构",
  office: "中央办公厅",
  functional: "党中央职能部门",
  affairs: "党中央办事机构",
  outpost: "中央派出机关",
  affiliate: "中央直属事业单位",
  subordinate: "中央直属机关下属机构",
};
const subtitle = computed(() => {
  if (!institution.value) return "";
  const category = institution.value.team === "party" && institution.value.party_category
    ? partyCategoryLabels[institution.value.party_category]
    : null;
  return `${rankLabels[institution.value.institution_rank] ?? institution.value.institution_rank} · ${category ?? typeLabels[institution.value.institution_type] ?? institution.value.institution_type}`;
});

function fullTitle(title: string): string {
  if (!institution.value) return title;
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
  const end = leader.end_date ? Date.parse(leader.end_date) : Date.parse(timeline.currentDate);
  const duration = Math.max(0, Math.floor((end - start) / 86_400_000));
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
    rank_label: rankLabels[rankLevel] ?? "正部级",
    is_acting: false,
    is_concurrent: false,
    is_plural: false,
    start_date: leader.start_date,
    end_date: leader.end_date,
    start_precision: "day",
    duration_days: duration,
    is_incumbent: !leader.end_date,
    is_provisional: false,
    is_roster_snapshot: false,
    status: leader.end_date ? "former" : "active",
    status_label: leader.end_date ? "离任" : "在任",
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
          <div class="label-eyebrow">中央机构</div>
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
            class="btn-icon"
            :class="{ 'border-vermilion/40 bg-vermilion/10 text-vermilion-bright': entityPanel.isPinned }"
            :title="entityPanel.isPinned ? '取消钉住' : '钉住以对比'"
            @click="entityPanel.togglePin"
          >
            <AppIcon name="pin" :size="14" />
          </button>
          <button class="btn-icon" title="关闭面板" @click="emit('close')">
            <AppIcon name="close" :size="15" />
          </button>
        </div>
      </div>
    </header>

    <div class="min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 py-4">
      <section>
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
        <p v-else class="text-[10px] text-paper-faint">该机构当前正职空缺。</p>
      </section>

      <section v-if="activeSeatTitle" class="mt-5 border-t border-white/10 pt-3">
        <button class="mb-2 inline-flex items-center gap-1 text-[9px] text-paper-faint hover:text-paper" @click="closeSeat">
          <AppIcon name="arrow-left" :size="10" /> 返回机构
        </button>
        <div class="flex items-center justify-between">
          <div class="label-eyebrow">历任 · {{ activeSeatTitle }}</div>
          <span class="text-[9px] text-paper-faint">{{ seatHistory.length }} 段</span>
        </div>
        <div v-if="seatHistory.length" class="mt-2 space-y-1">
          <LeaderRow
            v-for="member in seatHistory"
            :key="member.seat_key + member.start_date + member.officer.name"
            :member="member"
            @select="openPerson(member.officer.id)"
            @history="() => undefined"
          />
        </div>
        <p v-else class="mt-2 text-[10px] text-paper-faint">该岗位暂无历任记录。</p>
      </section>

      <p v-else class="mt-4 flex items-start gap-1.5 text-[9px] leading-relaxed text-paper-faint/65">
        <AppIcon name="info" :size="10" class="mt-px shrink-0" />
        这是机构页面；点击官员进入官员档案。点击任一正职的“历任”查看该岗位的历任领导。
      </p>
    </div>
  </div>
</template>

<style scoped>
.entity-member + .entity-member {
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  padding-top: 6px;
}
</style>
