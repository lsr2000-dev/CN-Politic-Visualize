<script setup lang="ts">
import { computed } from "vue";
import CentralCommitteeBadge from "./CentralCommitteeBadge.vue";
import PartyRoleBadge from "./PartyRoleBadge.vue";
import { showCentralCommittee, visiblePartyRoles } from "@/utils/partyRoles";
import type { CentralInstitution } from "@/types";

const props = defineProps<{
  node: CentralInstitution;
  childrenMap: Map<string | null, CentralInstitution[]>;
  depth: number;
}>();
const emit = defineEmits<{ select: [CentralInstitution] }>();

const children = computed(() => props.childrenMap.get(props.node.id) ?? []);
const isGroup = computed(() =>
  props.node.institution_type === "group" || props.node.institution_type.endsWith("_group"),
);
const isMilitary = computed(() => props.node.group_type === "military");
const isCollective = computed(() =>
  ["party:politburo_standing", "party:politburo", "party:secretariat"].includes(props.node.id),
);
function fullTitle(title: string): string {
  const isDepartment = ["ministry", "agency", "service", "institution", "special", "administration", "office", "public_institution", "admin_bureau", "outpost"].includes(props.node.institution_type);
  return isDepartment && !title.startsWith(props.node.name) ? `${props.node.name}${title}` : title;
}
function rankLabel(value: string): string {
  const labels: Record<string, string> = {
    national_leader: "正国级",
    vice_national_leader: "副国级",
    ministerial: "正部级",
    vice_ministerial: "副部级",
    departmental: "正地厅级",
    bureau: "局级",
  };
  return labels[value] ?? value;
}
</script>

<template>
  <div v-if="isGroup" class="central-group">
    <div class="central-group-title">
      <span class="h-2 w-[2px] bg-gold/70" />
      {{ node.name }}
      <span class="ml-auto text-[9px] tabular-nums text-paper-faint">{{ children.length }}</span>
    </div>
    <div class="central-children">
      <CentralOrgNode
        v-for="child in children"
        :key="child.id"
        :node="child"
        :children-map="childrenMap"
        :depth="depth + 1"
        @select="emit('select', $event)"
      />
    </div>
  </div>

  <div v-else class="central-node-wrap">
    <button class="central-node" :class="{ 'central-node-military': isMilitary }" @click="emit('select', node)">
      <div class="flex items-start justify-between gap-2">
        <div class="min-w-0">
          <div class="truncate text-[11px] font-medium text-paper">{{ node.name }}</div>
          <div class="mt-0.5 text-[8px] tracking-wider text-paper-faint">{{ rankLabel(node.institution_rank) }}</div>
        </div>
        <span class="text-[8px] text-paper-faint/60">{{ String(depth).padStart(2, "0") }}</span>
      </div>

      <div v-if="node.leaders.length" class="mt-1.5 space-y-1.5">
        <div v-for="leader in node.leaders" :key="leader.name + leader.title" class="flex flex-wrap items-center gap-1">
          <span class="text-[10px] text-paper-dim">{{ leader.name }}</span>
          <span class="text-[9px] text-paper-faint">{{ fullTitle(leader.title) }}</span>
          <PartyRoleBadge :roles="visiblePartyRoles(leader.party_roles, node.id)" compact />
          <CentralCommitteeBadge
            v-if="showCentralCommittee(leader.party_roles, node.id)"
            :committee="leader.central_committee"
            compact
          />
          <div v-if="leader.primary_post" class="w-full pl-0 text-[9px] leading-snug text-paper-faint/80">
            主要任职：{{ leader.primary_post }}
          </div>
        </div>
      </div>
      <div v-else class="mt-1.5 text-[9px] text-paper-faint/70">待收录</div>
    </button>

    <div v-if="children.length" class="central-children">
      <CentralOrgNode
        v-for="child in children"
        :key="child.id"
        :node="child"
        :children-map="childrenMap"
        :depth="depth + 1"
        @select="emit('select', $event)"
      />
    </div>
  </div>
</template>

<style scoped>
.central-group { margin-top: 10px; }
.central-group-title {
  display: flex; align-items: center; gap: 6px;
  font-size: 10px; letter-spacing: 0.08em; color: rgba(232, 224, 205, 0.7);
  padding: 4px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.central-children {
  margin-left: 10px; padding-left: 10px;
  border-left: 1px solid rgba(255, 255, 255, 0.07);
  display: flex; flex-direction: column; gap: 4px;
}
.central-node {
  width: 100%; text-align: left;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 6px; padding: 7px 8px;
  background: rgba(255, 255, 255, 0.022);
  transition: border-color 0.18s, background 0.18s;
}
.central-node:hover { border-color: rgba(176, 138, 74, 0.4); background: rgba(176, 138, 74, 0.05); }
.central-node-military { border-left: 2px solid rgba(141, 123, 176, 0.65); }
</style>
