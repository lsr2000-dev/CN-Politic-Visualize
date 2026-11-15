<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { useCentralStore } from "@/stores/central";
import { useTimelineStore } from "@/stores/timeline";
import { useMapStore } from "@/stores/map";
import CentralOrgNode from "./CentralOrgNode.vue";
import CentralOrgChart from "./CentralOrgChart.vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import type { CentralInstitution } from "@/types";

const central = useCentralStore();
const timeline = useTimelineStore();
const map = useMapStore();

function selectInstitution(inst: CentralInstitution): void {
  map.selectRegion(null);
  void central.selectInstitution(inst, timeline.currentDate);
}

const teams = [
  { key: "party", label: "党中央" },
  { key: "congress", label: "全国人大" },
  { key: "government", label: "国务院" },
  { key: "cppcc", label: "全国政协" },
  { key: "other", label: "其他中央" },
];

const institutions = computed(() => central.org?.institutions ?? []);
const tree = computed(() => {
  const map = new Map<string | null, typeof institutions.value>();
  for (const inst of institutions.value) {
    const key = inst.parent_id;
    if (!map.has(key)) map.set(key, []);
    map.get(key)!.push(inst);
  }
  return map;
});
const roots = computed(() => tree.value.get(null) ?? []);
const chartScroll = ref<HTMLDivElement | null>(null);
const chartScale = ref(0.9);

async function centerChart(): Promise<void> {
  await nextTick();
  const el = chartScroll.value;
  if (el) el.scrollLeft = Math.max(0, (el.scrollWidth - el.clientWidth) / 2);
}

watch(
  () => central.org,
  () => void centerChart(),
  { deep: false },
);

function open(team: string): void {
  void central.openTeam(team, timeline.currentDate);
}

watch(
  () => timeline.currentDate,
  (date) => {
    if (central.selectedTeam) void central.openTeam(central.selectedTeam, date);
  },
);

function close(): void {
  central.close();
}

function rankLabel(value: string): string {
  return ({
    national_leader: "正国级",
    vice_national_leader: "国家级副职",
    ministerial: "正部级",
    theater_principal: "正战区级",
  } as Record<string, string>)[value] ?? value;
}
</script>

<template>
  <Teleport to="body">
    <Transition name="slide-panel">
      <aside v-if="central.selectedTeam && !central.selectedInstitution" class="central-panel" aria-label="中央机构组织架构">
      <header class="central-head">
        <div class="flex items-center gap-2">
          <span class="seal h-7 w-7 rounded-sm text-[13px]">央</span>
          <div>
            <div class="label-eyebrow">CENTRAL ORG / 中央组织架构</div>
            <h2 class="font-display text-[18px] leading-tight text-paper">
              {{ central.overview?.teams[central.selectedTeam]?.label ?? "中央机构" }}
            </h2>
            <div class="mt-0.5 text-[9px] text-paper-faint">
              正职覆盖 {{ central.overview?.coverage.filled ?? "—" }} / {{ central.overview?.coverage.required ?? "—" }}
              <span v-if="central.overview?.coverage.missing" class="text-gold">
                · 待补 {{ central.overview.coverage.missing }}
              </span>
            </div>
          </div>
        </div>
        <button class="btn-icon" title="关闭" @click="close"><AppIcon name="close" :size="14" /></button>
      </header>

      <div class="central-tabs">
        <button
          v-for="team in teams"
          :key="team.key"
          class="central-tab"
          :class="{ 'central-tab-active': central.selectedTeam === team.key }"
          @click="open(team.key)"
        >
          {{ team.label }}
        </button>
      </div>

      <div class="central-body">
        <div v-if="central.loading" class="p-6 text-center text-[11px] text-paper-faint">正在装载组织架构…</div>
        <div v-else-if="central.error" class="p-6 text-center text-[11px] text-vermilion-bright">{{ central.error }}</div>
        <div v-else class="central-tree">
          <div class="mb-2 flex items-center justify-end gap-1">
            <button class="btn-ghost h-6 px-2 text-[9px]" @click="chartScale = Math.max(0.45, chartScale - 0.08)">−</button>
            <span class="w-9 text-center text-[9px] tabular-nums text-paper-faint">{{ Math.round(chartScale * 100) }}%</span>
            <button class="btn-ghost h-6 px-2 text-[9px]" @click="chartScale = Math.min(1.2, chartScale + 0.08)">+</button>
          </div>
          <div ref="chartScroll" class="hidden overflow-auto pb-4 md:block">
            <div
              class="flex w-full justify-center px-8"
              :style="{ transform: `scale(${chartScale})`, transformOrigin: 'top center' }"
            >
              <CentralOrgChart
                v-for="node in roots"
                :key="node.id"
                :node="node"
                :children-map="tree"
                :depth="1"
                @select="selectInstitution"
              />
            </div>
          </div>
          <div class="md:hidden">
            <CentralOrgNode
              v-for="node in roots"
              :key="node.id"
              :node="node"
              :children-map="tree"
              :depth="1"
              @select="selectInstitution"
            />
          </div>
        </div>
      </div>
    </aside>
    </Transition>
  </Teleport>
</template>

<style scoped>
.central-panel {
  position: fixed; right: 0; top: 64px; bottom: 0; z-index: 70;
  width: min(100vw, 560px);
  display: flex; flex-direction: column;
  border-left: 1px solid rgba(255, 255, 255, 0.09);
  background: rgba(9, 12, 17, 0.96);
  backdrop-filter: blur(20px);
  box-shadow: -24px 0 60px -30px rgba(0, 0, 0, 0.9);
}
.central-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 16px 10px; border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.central-tabs {
  display: flex; gap: 4px; padding: 7px 12px; overflow-x: auto;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.central-tab {
  flex: 0 0 auto; border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 4px; padding: 3px 7px; font-size: 10px; color: rgba(232, 224, 205, 0.55);
}
.central-tab-active { border-color: rgba(200, 73, 47, 0.55); color: #f1ece1; background: rgba(200, 73, 47, 0.1); }
.central-body { min-height: 0; flex: 1; overflow-y: auto; padding: 10px 14px 22px; }
.central-tree { display: flex; flex-direction: column; gap: 4px; }
.central-detail {
  margin-top: 12px; border: 1px solid rgba(176, 138, 74, 0.24);
  border-radius: 8px; background: rgba(176, 138, 74, 0.05); padding: 10px;
}
@media (max-width: 640px) {
  .central-panel { top: 56px; width: 100vw; }
}
</style>
