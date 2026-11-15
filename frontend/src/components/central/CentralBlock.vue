<script setup lang="ts">
import { computed, onMounted, watch } from "vue";
import { useCentralStore } from "@/stores/central";
import { useMapStore } from "@/stores/map";
import { useTimelineStore } from "@/stores/timeline";

const central = useCentralStore();
const map = useMapStore();
const timeline = useTimelineStore();

const mainTeams = ["party", "congress", "government", "cppcc"] as const;
function teamStart(team: string): string {
  return central.overview?.team_coverage?.[team]?.start ?? "2012-11-08";
}
function teamAvailable(team: string): boolean {
  return timeline.currentDate >= teamStart(team);
}
const available = computed(() => mainTeams.some((team) => teamAvailable(team)));
const otherAvailable = computed(() => teamAvailable("other"));

function open(team: string): void {
  if (!teamAvailable(team)) return;
  map.selectRegion(null);
  void central.openTeam(team, timeline.currentDate);
}

function load(date: string): void {
  if (date >= "2012-11-08") void central.loadOverview(date);
}

function teamFloor(team: string): string {
  return teamStart(team).slice(0, 7).replace("-", ".");
}

onMounted(() => load(timeline.currentDate));
watch(() => timeline.currentDate, load);
</script>

<template>
  <div class="central-block">
    <div class="mb-1.5 flex items-center gap-2">
      <span class="h-3 w-[2px] bg-gold" />
      <span class="label-eyebrow">CENTRAL / 中央领导机构</span>
    </div>

    <div class="grid grid-cols-2 gap-1.5">
      <button
        v-for="key in mainTeams"
        :key="key"
        class="central-tile group"
        :disabled="!teamAvailable(key)"
        :class="{ 'central-tile-active': central.selectedTeam === key, 'opacity-45': !teamAvailable(key) }"
        @click.stop="open(key)"
      >
        <div class="flex items-center justify-between gap-1">
          <span class="text-[11px] font-medium text-paper">
            {{ central.overview?.teams[key]?.label ?? key }}
          </span>
          <span class="text-[9px] tabular-nums text-paper-faint">
            {{ central.overview?.teams[key]?.count ?? "—" }}
          </span>
        </div>
        <div class="mt-1 truncate text-[10px] text-paper-dim">
          {{ central.overview?.teams[key]?.leader?.name ?? "待收录" }}
        </div>
        <div class="mt-0.5 text-[8px] tracking-wider text-paper-faint/70">
          {{ central.overview?.teams[key]?.leader?.title ?? (teamAvailable(key) ? "点击查看架构" : teamFloor(key) + " 起收录") }}
        </div>
      </button>
    </div>

    <div class="mt-1.5 flex flex-wrap gap-1">
      <button
        v-for="item in central.overview?.other ?? []"
        :key="item.key"
        class="rounded border border-white/10 bg-ink-900/70 px-1.5 py-1 text-[9px] text-paper-faint transition hover:border-gold/35 hover:text-paper disabled:opacity-40"
        :disabled="!otherAvailable"
        @click.stop="open('other')"
      >
        {{ item.label }} <span class="tabular-nums opacity-60">{{ item.count }}</span>
      </button>
    </div>

    <p v-if="central.error" class="mt-1 text-[9px] text-vermilion-bright">{{ central.error }}</p>
    <p v-if="!available" class="mt-1 text-[9px] text-paper-faint">中央机构图从 2012-11-08 开始</p>
  </div>
</template>

<style scoped>
.central-block {
  width: 286px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  background: rgba(9, 12, 17, 0.82);
  padding: 10px;
  backdrop-filter: blur(14px);
  box-shadow: 0 18px 46px -20px rgba(0, 0, 0, 0.85);
}
.central-tile {
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 7px;
  background: rgba(255, 255, 255, 0.025);
  padding: 7px 8px;
  text-align: left;
  transition: border-color 0.18s, background 0.18s;
}
.central-tile:hover {
  border-color: rgba(176, 138, 74, 0.45);
  background: rgba(176, 138, 74, 0.06);
}
.central-tile-active {
  border-color: rgba(224, 112, 80, 0.7);
  background: rgba(200, 73, 47, 0.1);
}
@media (max-width: 768px) {
  .central-block { width: min(286px, calc(100vw - 24px)); }
}
</style>
