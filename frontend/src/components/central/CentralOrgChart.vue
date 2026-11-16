<script setup lang="ts">
import { computed } from "vue";
import PartyRoleBadge from "./PartyRoleBadge.vue";
import CentralCommitteeBadge from "./CentralCommitteeBadge.vue";
import { showCentralCommittee, visiblePartyRoles } from "@/utils/partyRoles";
import { useAppStore } from "@/stores/app";
import { useCentralStore } from "@/stores/central";
import type { CentralInstitution } from "@/types";

const app = useAppStore();
const central = useCentralStore();

const props = defineProps<{
  node: CentralInstitution;
  childrenMap: Map<string | null, CentralInstitution[]>;
  depth?: number;
}>();
const emit = defineEmits<{ select: [CentralInstitution] }>();

const children = computed(() => props.childrenMap.get(props.node.id) ?? []);
const isGroup = computed(() =>
  props.node.institution_type === "group" || props.node.institution_type.endsWith("_group"),
);
const isCollective = computed(() =>
  ["party:politburo_standing", "party:politburo", "party:secretariat"].includes(props.node.id),
);
function fullTitle(title: string): string {
  if (props.node.id === "party:general_secretary") return props.node.name;
  const isDepartment = ["ministry", "agency", "service", "institution", "special", "administration", "office", "public_institution", "admin_bureau", "outpost"].includes(props.node.institution_type);
  return isDepartment && !title.startsWith(props.node.name) ? `${props.node.name}${title}` : title;
}
function rankLabel(value: string): string {
  return app.vocabulary?.ranks[value] ?? value;
}
</script>

<template>
  <div class="org-branch">
    <button
      v-if="!isGroup"
      class="org-card"
      :class="{ 'org-card-collective': isCollective, 'org-card-selected': central.selectedInstitution?.id === node.id }"
      @click="emit('select', node)"
    >
      <div class="org-card-title">{{ node.short_name || node.name }}</div>
      <div class="org-card-rank">{{ rankLabel(node.institution_rank) }}</div>

      <div v-if="node.leaders.length" class="mt-1 space-y-0.5">
        <div v-for="leader in node.leaders" :key="leader.name + leader.title" class="org-leader">
          <div class="flex flex-wrap items-center gap-1">
            <span class="text-[10px] text-paper">{{ leader.name }}</span>
            <PartyRoleBadge :roles="visiblePartyRoles(leader.party_roles, node.id)" compact />
            <CentralCommitteeBadge
              v-if="showCentralCommittee(leader.party_roles, node.id)"
              :committee="leader.central_committee"
              compact
            />
          </div>
          <div v-if="leader.primary_post" class="text-[8px] leading-snug text-paper-faint/75">
            {{ leader.primary_post }}
          </div>
          <div v-else class="text-[8px] text-paper-faint/60">{{ fullTitle(leader.title) }}</div>
        </div>
      </div>
      <div v-else-if="node.id === 'party:central_committee'" class="mt-1 text-[8px] text-paper-faint/60">集体领导机构 · 总书记单列</div>
      <div v-else class="mt-1 text-[8px] text-paper-faint/60">待收录</div>
    </button>

    <div v-else class="org-group-label">
      <span class="h-2 w-[2px] bg-gold/70" />
      {{ node.name }}
      <span class="text-paper-faint/60">({{ children.length }})</span>
    </div>

    <div v-if="children.length" class="org-children">
      <CentralOrgChart
        v-for="child in children"
        :key="child.id"
        :node="child"
        :children-map="childrenMap"
        :depth="(depth ?? 1) + 1"
        @select="emit('select', $event)"
      />
    </div>
  </div>
</template>

<style scoped>
.org-branch {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  width: 100%;
  flex: 0 0 auto;
}
.org-card {
  width: 158px;
  min-height: 42px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 7px;
  background: rgba(16, 22, 30, 0.95);
  padding: 6px 7px;
  text-align: left;
  transition: border-color 0.18s, background 0.18s;
}
.org-card:hover {
  border-color: rgba(176, 138, 74, 0.55);
  background: rgba(176, 138, 74, 0.07);
}
.org-card-collective {
  width: 180px;
  border-color: rgba(200, 73, 47, 0.42);
  background: rgba(200, 73, 47, 0.06);
}
.org-card-selected {
  border-color: rgba(176, 138, 74, 0.9);
  background: rgba(176, 138, 74, 0.14);
  box-shadow: 0 0 0 1px rgba(176, 138, 74, 0.25);
}
.org-card-title {
  font-size: 10px;
  color: #f1ece1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.org-card-rank {
  margin-top: 1px;
  font-size: 7px;
  letter-spacing: 0.06em;
  color: rgba(232, 224, 205, 0.4);
  text-transform: uppercase;
}
.org-leader + .org-leader {
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  padding-top: 3px;
  margin-top: 3px;
}
.org-children {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 5px;
  position: relative;
  margin-top: 8px;
  margin-left: 18px;
  padding-left: 12px;
  border-left: 1px solid rgba(176, 138, 74, 0.35);
  max-width: calc(100% - 18px);
}
.org-children > .org-branch {
  position: relative;
}
.org-children > .org-branch::before {
  content: "";
  position: absolute;
  top: 12px;
  left: -12px;
  width: 12px;
  border-top: 1px solid rgba(176, 138, 74, 0.35);
}
.org-group-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 9px;
  letter-spacing: 0.08em;
  color: rgba(232, 224, 205, 0.75);
  white-space: nowrap;
  padding: 4px 6px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
</style>
