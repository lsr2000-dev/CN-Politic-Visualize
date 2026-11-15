<script setup lang="ts">
import { computed } from "vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import PartyRoleBadge from "@/components/central/PartyRoleBadge.vue";
import CentralCommitteeBadge from "@/components/central/CentralCommitteeBadge.vue";
import { useCentralStore } from "@/stores/central";
import { useMapStore } from "@/stores/map";
import { useTimelineStore } from "@/stores/timeline";
import { showCentralCommittee, visiblePartyRoles, partyRankLevel } from "@/utils/partyRoles";
import type { CentralInstitution } from "@/types";

const emit = defineEmits<{ (event: "close"): void }>();

const central = useCentralStore();
const map = useMapStore();
const timeline = useTimelineStore();

const teamLabel = computed(() => {
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
    { label: "十八届", date: "2012-11-08" },
    { label: "十九届", date: "2017-10-25" },
    { label: "二十届", date: "2022-10-16" },
  ];
});
function activeTerm(date: string): boolean {
  const index = termAnchors.value.findIndex((item) => item.date === date);
  const current = timeline.currentDate;
  const next = termAnchors.value[index + 1]?.date;
  return current >= date && (!next || current < next);
}
const partyGroupLabels: Record<string, string> = {
  leadership: "中央领导机构",
  office: "中央办公厅",
  functional: "党中央职能部门",
  affairs: "党中央办事机构",
  outpost: "中央派出机关",
  affiliate: "中央直属事业单位",
  subordinate: "中央直属机关下属机构",
};
const partyGroupOrder = ["leadership", "office", "functional", "affairs", "outpost", "affiliate", "subordinate"];
async function selectTerm(date: string): Promise<void> {
  timeline.setDate(date);
  if (central.selectedTeam) await central.openTeam(central.selectedTeam, date);
}
function partyCategoryLabel(institution: CentralInstitution): string {
  if (central.selectedTeam === "party" && institution.party_category) {
    return partyGroupLabels[institution.party_category] ?? institution.party_category;
  }
  return typeLabel(institution.institution_type, institution.name);
}
const groupLabels: Record<string, string> = {
  party: "党中央",
  congress: "全国人大",
  government: "国务院",
  cppcc: "全国政协",
  judicial: "两高",
  mass: "群团",
  military: "军委",
  supervision: "纪委监委",
  deliberative: "议事协调",
  other: "其他中央机构",
  leadership: "领导机构",
  ministry: "国务院组成部门",
  agency: "国务院直属机构",
  office: "国务院办事机构",
  public_institution: "国务院直属事业单位",
  special: "国务院特设机构",
  committee: "专门委员会",
  affiliate: "中央直属事业单位",
  party_affairs: "中央办事机构",
  party_outpost: "中央派出机关",
  party_subordinate: "中央直属机关下属机构",
  administration: "国务院直属机构（副部级）",
  admin_bureau_group: "国务院部委管理的国家局",
  admin_bureau: "国务院部委管理的国家局",
  outpost_group: "国务院派出机构",
  outpost: "国务院派出机构",
};
const rankLabels: Record<string, string> = {
  national_leader: "正国级",
  vice_national_leader: "副国级",
  ministerial: "正部级",
  vice_ministerial: "副部级",
  departmental: "正地厅级",
  bureau: "局级",
};
const typeLabels: Record<string, string> = {
  state_council_leadership: "国务院领导",
  ministry: "组成部门",
  ministry_group: "组成部门",
  agency: "直属机构",
  agency_group: "直属机构",
  service: "办事机构",
  institution: "直属事业单位",
  special: "特设机构",
  commission: "专门委员会",
  administration: "国务院直属机构",
  office: "国务院办事机构",
  public_institution: "国务院直属事业单位",
  admin_bureau: "部委管理的国家局",
  outpost: "国务院派出机构",
  academy: "军事院校",
  armed_police: "武警部队",
  court: "人民法院",
  procuratorate: "人民检察院",
  cppcc_committee: "政协专门委员会",
  cppcc_leadership: "政协领导",
  deliberative_committee: "议事协调机构",
  deliberative_office: "议事协调办公室",
  mass_organization: "群团组织",
  military_agency: "军委机关",
  military_leadership: "军委领导",
  npc_committee: "人大专门委员会",
  npc_leadership: "全国人大领导",
  party_affiliate: "中央直属事业单位",
  party_outpost: "中央派出机关",
  party_subordinate: "中央直属机关下属机构",
  party_agency: "中央工作机关",
  party_leadership: "党中央领导",
  theater: "战区",
};
function rankLabel(value: string): string {
  return rankLabels[value] ?? value;
}
function displayRank(institution: CentralInstitution): string {
  const override = institution.leaders.find((leader) => leader.rank_override)?.rank_override;
  return rankLabel(override ?? institution.institution_rank);
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
  return typeLabels[value] ?? value;
}
function fullTitle(institution: CentralInstitution, title: string): string {
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
      ? institution.party_category || institution.group_type || "other"
      : institution.group_type || "other";
    if (!byKey.has(key)) byKey.set(key, []);
    byKey.get(key)!.push(institution);
  }
  const entries = [...byKey.entries()];
  if (central.selectedTeam === "party") {
    entries.sort((a, b) => partyGroupOrder.indexOf(a[0]) - partyGroupOrder.indexOf(b[0]));
  }
  for (const [key, items] of entries) {
    result.push({
      key,
      label: central.selectedTeam === "party"
        ? partyGroupLabels[key] ?? groupLabels[key] ?? key
        : groupLabels[key] ?? key,
      items: items.sort((a, b) => a.sort_order - b.sort_order),
    });
  }
  return result;
});

function open(institution: CentralInstitution): void {
  map.selectRegion(null);
  void central.selectInstitution(institution, timeline.currentDate);
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
              @click="open(institution)"
            >
              <div class="min-w-0 flex-1">
                <div class="text-[11px] text-paper">
                  {{ institution.name }}
                  <span
                    v-if="institution.verification_status === 'provisional'"
                    class="ml-1 rounded border border-amber-400/30 px-1 py-px text-[8px] text-amber-300/90"
                  >待核验</span>
                  <span
                    v-else-if="institution.verification_status === 'unverified'"
                    class="ml-1 rounded border border-white/15 px-1 py-px text-[8px] text-paper-faint"
                  >未核验</span>
                </div>
                <div class="mt-0.5 text-[8px] tracking-wide text-paper-faint">
                  {{ displayRank(institution) }} · {{ partyCategoryLabel(institution) }}
                </div>
                <div v-if="institution.leaders.length" class="mt-1 space-y-0.5">
                  <div
                    v-for="leader in institution.leaders"
                    :key="leader.name + leader.title"
                    class="central-team-leader"
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
                    </div>
                  </div>
                </div>
                <div v-else-if="isNotYetCreated(institution)" class="mt-1 text-[9px] text-paper-faint">
                  {{ institution.created_at ? `${createdLabel(institution)} 组建，当前时点尚未设立` : `历史数据自 ${createdLabel(institution)} 起` }}
                </div>
                <div v-else-if="isAbolished(institution)" class="mt-1 text-[9px] text-paper-faint">该机构已撤销</div>
                <div v-else class="mt-1 text-[9px] text-paper-faint">正职空缺</div>
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
</style>
