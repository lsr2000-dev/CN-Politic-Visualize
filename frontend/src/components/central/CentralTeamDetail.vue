<script setup lang="ts">
import { computed } from "vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import PartyRoleBadge from "@/components/central/PartyRoleBadge.vue";
import CentralCommitteeBadge from "@/components/central/CentralCommitteeBadge.vue";
import { useCentralStore } from "@/stores/central";
import { useAppStore } from "@/stores/app";
import { useMapStore } from "@/stores/map";
import { useTimelineStore } from "@/stores/timeline";
import { showCentralCommittee, visiblePartyRoles, partyRankLevel } from "@/utils/partyRoles";
import type { CentralInstitution } from "@/types";

const emit = defineEmits<{ (event: "close"): void }>();

const central = useCentralStore();
const app = useAppStore();
const map = useMapStore();
const timeline = useTimelineStore();

const teamLabel = computed(() => {
  if (central.selectedTeam === "party") return "中国共产党中央委员会";
  if (central.selectedTeam === "other") return "其他中央机构";
  return central.overview?.teams[central.selectedTeam ?? ""]?.label ?? "中央机构";
});
const institutionCount = computed(() =>
  groups.value.reduce((total, group) => total + group.items.length, 0),
);
const termAnchors = computed(() => {
  if (central.selectedTeam === "government") {
    return [
      { label: "2013 内阁", date: "2013-03-15" },
      { label: "2018 内阁", date: "2018-03-19" },
      { label: "2023 内阁", date: "2023-03-12" },
    ];
  }
  return [
    { label: "十八届", date: "2012-11-15" },
    { label: "十九届", date: "2017-10-25" },
    { label: "二十届", date: "2022-10-23" },
  ];
});
function activeTerm(date: string): boolean {
  const index = termAnchors.value.findIndex((item) => item.date === date);
  const current = timeline.currentDate;
  const next = termAnchors.value[index + 1]?.date;
  return current >= date && (!next || current < next);
}
const partyGroupLabels = computed(() => app.vocabulary?.party_categories ?? {});
const groupLabels = computed(() => app.vocabulary?.group_labels ?? {});
const partyGroupOrder = [
  "composition",
  "leaders",
  "standing",
  "working",
  "departments",
  "discipline",
  "affairs",
  "outpost",
  "affiliate",
  "subordinate",
];
const partyGroupNames: Record<string, string> = {
  composition: "组成人员",
  leaders: "领导人员",
  standing: "常设机构",
  working: "工作机构",
  departments: "职能部门",
  discipline: "纪律检查机关",
  affairs: "办事机构",
  outpost: "派出机关",
  affiliate: "直属事业单位",
  subordinate: "直属机关下属机构",
};
const partyItemOrder: Record<string, string[]> = {
  composition: ["party:central_committee"],
  leaders: ["party:general_secretary"],
  standing: ["party:politburo_standing", "party:politburo", "party:secretariat"],
  working: ["party:general_office"],
};
function partyGroupKey(institution: CentralInstitution): string {
  if (institution.id === "party:central_committee") return "composition";
  if (institution.id === "party:general_secretary") return "leaders";
  if (["party:politburo_standing", "party:politburo", "party:secretariat"].includes(institution.id)) {
    return "standing";
  }
  if (institution.id === "party:general_office" || institution.party_category === "office") {
    return "working";
  }
  if (institution.party_category === "functional") return "departments";
  if (institution.id === "party:discipline") return "discipline";
  return institution.party_category || institution.group_type || "other";
}
function partyItemRank(institution: CentralInstitution, key: string): number {
  const order = partyItemOrder[key] ?? [];
  const index = order.indexOf(institution.id);
  return index >= 0 ? index : 999;
}
function selectTerm(date: string): void {
  timeline.setDate(date);
}
function partyCategoryLabel(institution: CentralInstitution): string {
  if (institution.id === "party:central_committee") return "权力机关";
  if (central.selectedTeam === "party") {
    const key = partyGroupKey(institution);
    return partyGroupNames[key] ?? partyGroupLabels.value[key] ?? key;
  }
  return typeLabel(institution.institution_type, institution.name);
}
function rankLabel(value: string): string {
  return app.vocabulary?.ranks[value] ?? value;
}
function displayRank(institution: CentralInstitution): string {
  const override = institution.leaders.find((leader) => leader.rank_override)?.rank_override;
  return rankLabel(override ?? institution.institution_rank);
}
function cardMeta(institution: CentralInstitution): string {
  if (institution.id === "party:central_committee") return "权力机关";
  return `${displayRank(institution)} · ${partyCategoryLabel(institution)}`;
}
function leaderRank(leader: CentralInstitution["leaders"][number], institution: CentralInstitution): string {
  const partyLevel = partyRankLevel(leader.party_roles);
  if (partyLevel) return rankLabel(partyLevel);
  if (leader.rank_override) return rankLabel(leader.rank_override);
  return rankLabel(institution.institution_rank);
}
function typeLabel(value: string, name = ""): string {
  if (value === "administration") {
    if (name === "海关总署") return "直属国家总署";
    if (name.endsWith("总局")) return "直属国家总局";
    if (name.endsWith("局")) return "直属国家局";
    if (name.endsWith("署")) return "直属国家署";
  }
  return app.vocabulary?.institution_types[value]?.short ?? value;
}
function fullTitle(institution: CentralInstitution, title: string): string {
  if (institution.id === "party:general_secretary") return institution.name;
  if (institution.institution_type === "state_council_leadership") {
    if (institution.name.endsWith(title)) return institution.name;
    return `${institution.short_name || institution.name}${title}`;
  }
  const isDepartment = [
    "ministry", "agency", "service", "institution", "special",
    "administration", "office", "public_institution", "admin_bureau", "outpost",
  ].includes(institution.institution_type);
  return isDepartment && !title.startsWith(institution.name) ? `${institution.name}${title}` : title;
}
function isNotYetCreated(institution: CentralInstitution): boolean {
  return institution.status_at === "not_yet";
}
function isAbolished(institution: CentralInstitution): boolean {
  return institution.status_at === "abolished";
}
function createdLabel(institution: CentralInstitution): string {
  const value = institution.created_at ?? institution.valid_from;
  return value?.slice(0, 7).replace("-", ".") ?? "";
}

const groups = computed(() => {
  const result: Array<{ key: string; label: string; items: CentralInstitution[] }> = [];
  const byKey = new Map<string, CentralInstitution[]>();
  for (const institution of central.org?.institutions ?? []) {
    if (institution.institution_type === "group" || institution.institution_type.endsWith("_group")) continue;
    const key = central.selectedTeam === "party"
      ? partyGroupKey(institution)
      : institution.group_type || "other";
    if (!byKey.has(key)) byKey.set(key, []);
    byKey.get(key)!.push(institution);
  }
  const entries = [...byKey.entries()];
  if (central.selectedTeam === "party") {
    entries.sort((a, b) => partyGroupOrder.indexOf(a[0]) - partyGroupOrder.indexOf(b[0]));
  }
  for (const [key, items] of entries) {
    if (central.selectedTeam === "party") {
      items.sort((a, b) => partyItemRank(a, key) - partyItemRank(b, key) || a.sort_order - b.sort_order);
    } else {
      items.sort((a, b) => a.sort_order - b.sort_order);
    }
    result.push({
      key,
      label: central.selectedTeam === "party"
        ? partyGroupNames[key] ?? partyGroupLabels.value[key] ?? groupLabels.value[key] ?? key
        : groupLabels.value[key] ?? key,
      items,
    });
  }
  return result;
});

function open(institution: CentralInstitution): void {
  map.selectRegion(null);
  void central.selectInstitution(institution, timeline.currentDate);
}
function cardMembers(institution: CentralInstitution): CentralInstitution["leaders"] {
  return institution.roster_members?.length
    ? institution.roster_members
    : institution.elected_members?.length
      ? institution.elected_members
      : institution.leaders;
}
</script>

<template>
  <div class="flex h-full min-h-0 flex-col">
    <header class="relative shrink-0 border-b border-white/[0.07] px-5 pb-4 pt-5">
      <div class="flex items-start justify-between gap-3">
        <div>
          <div class="label-eyebrow">中央领导机构</div>
          <h1 class="mt-1.5 font-display text-[30px] leading-none tracking-wide text-paper">{{ teamLabel }}</h1>
          <div class="mt-2 flex flex-wrap items-center gap-1.5">
            <span class="chip">{{ institutionCount }} 个机构节点</span>
            <span class="chip">点击机构查看详情</span>
            <span class="ml-auto flex flex-wrap gap-1">
              <button
                v-for="term in termAnchors"
                :key="term.date"
                class="rounded border px-1.5 py-0.5 text-[9px] transition"
                :class="activeTerm(term.date)
                  ? 'border-gold/45 bg-gold/10 text-gold'
                  : 'border-white/10 text-paper-faint hover:border-gold/30'"
                @click="selectTerm(term.date)"
              >
                {{ term.label }}
              </button>
            </span>
          </div>
        </div>
        <button class="btn-icon" title="关闭面板" @click="emit('close')">
          <AppIcon name="close" :size="15" />
        </button>
      </div>
    </header>

    <div class="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-3">
      <div v-if="central.loading" class="py-12 text-center text-[11px] text-paper-faint">正在装载中央机构…</div>
      <div v-else-if="central.error" class="py-12 text-center text-[11px] text-vermilion-bright">{{ central.error }}</div>
      <template v-else>
        <section v-for="group in groups" :key="group.key" class="mb-4">
          <div class="mb-1.5 flex items-center gap-2 px-1">
            <span class="h-2.5 w-[2px] bg-gold/70" />
            <span class="text-[10px] tracking-[0.12em] text-paper-dim">{{ group.label }}</span>
            <span class="text-[9px] tabular-nums text-paper-faint">{{ group.items.length }}</span>
          </div>
          <div class="space-y-1">
            <button
              v-for="institution in group.items"
              :key="institution.id"
              class="central-team-row"
              :class="{ 'central-team-row-active': central.selectedInstitution?.id === institution.id }"
              @click="open(institution)"
            >
              <div class="min-w-0 flex-1">
                <div class="flex items-center gap-1 text-[11px] text-paper">
                  <span class="truncate">{{ institution.name }}</span>
                  <span v-if="central.detailLoading && central.selectedInstitution?.id === institution.id" class="text-[8px] text-gold">加载中…</span>
                  <span
                    v-if="institution.verification_status === 'provisional'"
                    class="ml-1 rounded border border-amber-400/30 px-1 py-px text-[8px] text-amber-300/90"
                  >待核验</span>
                  <span
                    v-else-if="institution.verification_status === 'unverified'"
                    class="ml-1 rounded border border-white/15 px-1 py-px text-[8px] text-paper-faint"
                  >未核验</span>
                  <span
                    v-if="institution.composition"
                    class="ml-auto flex shrink-0 items-baseline gap-0.5 text-paper-dim"
                    :title="`机构委员人数：${institution.composition.current} 人`"
                    :aria-label="`机构委员人数：${institution.composition.current} 人`"
                  >
                    <span class="text-[12px] font-medium tabular-nums">{{ institution.composition.display }}</span>
                    <span class="text-[10px] text-paper-faint">人</span>
                  </span>
                </div>
                <div class="mt-0.5 text-[8px] tracking-wide text-paper-faint">
                  {{ cardMeta(institution) }}
                </div>
                <div v-if="cardMembers(institution).length" class="mt-1 space-y-0.5">
                  <div
                    v-for="leader in cardMembers(institution)"
                    :key="leader.name + leader.title"
                    class="central-team-leader"
                    :class="{ 'central-team-expelled': leader.member_status === 'expelled' }"
                  >
                    <span class="leader-name text-[10px] text-paper-dim">{{ leader.name }}</span>
                    <div class="leader-content">
                      <span class="leader-title text-[9px] text-paper-faint">{{ fullTitle(institution, leader.title) }}</span>
                      <span class="whitespace-nowrap rounded border border-white/10 px-1 py-px text-[8px] text-paper-faint">
                        {{ leaderRank(leader, institution) }}
                      </span>
                      <PartyRoleBadge :roles="visiblePartyRoles(leader.party_roles, institution.id)" compact />
                      <CentralCommitteeBadge
                        v-if="showCentralCommittee(leader.party_roles, institution.id)"
                        :committee="leader.central_committee"
                        compact
                      />
                      <span
                        v-if="leader.member_status_label"
                        class="whitespace-nowrap rounded border px-1 py-px text-[8px]"
                        :class="leader.member_status === 'added'
                          ? 'border-gold/45 bg-gold/10 text-gold'
                          : 'border-vermilion/40 bg-vermilion/10 text-vermilion-bright'"
                      >{{ leader.member_status_label }}</span>
                    </div>
                  </div>
                </div>
                <div v-if="institution.membership_changes?.length" class="mt-1.5 space-y-1 border-t border-white/[0.06] pt-1.5">
                  <div v-for="change in institution.membership_changes" :key="change.label">
                    <div
                      class="text-[8px] tracking-wide"
                      :class="change.change_type === 'removed' ? 'text-vermilion-bright/80' : 'text-jade/80'"
                    >{{ change.label }}</div>
                    <div class="mt-0.5 flex flex-wrap gap-x-2 gap-y-0.5">
                      <span
                        v-for="name in change.members"
                        :key="name"
                        class="text-[9px]"
                        :class="change.change_type === 'removed'
                          ? 'text-paper-faint/55 line-through'
                          : 'text-paper-dim'"
                      >{{ name }}</span>
                    </div>
                  </div>
                </div>
                <template v-if="!cardMembers(institution).length">
                  <div v-if="isNotYetCreated(institution)" class="mt-1 text-[9px] text-paper-faint">
                    {{ institution.created_at ? `${createdLabel(institution)} 组建，当前时点尚未设立` : `历史数据自 ${createdLabel(institution)} 起` }}
                  </div>
                  <div v-else-if="isAbolished(institution)" class="mt-1 text-[9px] text-paper-faint">该机构已撤销</div>
                  <div v-else-if="institution.id === 'party:central_committee'" class="mt-1 text-[9px] text-paper-faint">集体领导机构 · 总书记单列</div>
                </template>
              </div>
              <AppIcon name="chevron-right" :size="12" class="shrink-0 text-paper-faint" />
            </button>
          </div>
        </section>
      </template>
    </div>
  </div>
</template>

<style scoped>
.central-team-row {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 8px;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.018);
  padding: 8px 10px;
  text-align: left;
  transition: border-color 0.18s, background 0.18s;
}
.central-team-row:hover {
  border-color: rgba(176, 138, 74, 0.4);
  background: rgba(176, 138, 74, 0.05);
}
.central-team-row-active {
  border-color: rgba(176, 138, 74, 0.65);
  background: rgba(176, 138, 74, 0.1);
  box-shadow: inset 2px 0 0 rgba(176, 138, 74, 0.8);
}
.central-team-leader {
  display: flex;
  align-items: flex-start;
  gap: 4px;
}
.leader-name {
  flex: 0 0 48px;
  width: 48px;
  line-height: 1.5;
  white-space: normal;
  word-break: break-word;
}
.leader-content {
  display: flex;
  flex: 1 1 auto;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
  min-width: 0;
}
.leader-title {
  line-height: 1.5;
  white-space: normal;
  word-break: break-word;
}
.central-team-expelled .leader-name,
.central-team-expelled .leader-title {
  text-decoration: line-through;
  color: rgba(232, 224, 205, 0.38);
}
.central-team-expelled .leader-content {
  opacity: 0.68;
}
</style>
