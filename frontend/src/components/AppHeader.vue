<script setup lang="ts">
import { computed } from "vue";
import AppIcon from "./ui/AppIcon.vue";
import { useAppStore } from "@/stores/app";
import { useMapStore } from "@/stores/map";
import { formatDate } from "@/utils/format";
import type { ViewMode } from "@/types";

const app = useAppStore();
const map = useMapStore();

const modes: Array<{ value: ViewMode; icon: "panel" | "float" | "maximize"; label: string }> = [
  { value: "sidebar", icon: "panel", label: "侧边栏" },
  { value: "floating", icon: "float", label: "浮动窗" },
  { value: "fullscreen", icon: "maximize", label: "全屏" },
];

const coverage = computed(() =>
  formatDate(app.meta?.dataset.coverage_end, "YYYY.MM.DD"),
);

const currentMode = computed(
  () => modes.find((mode) => mode.value === map.viewMode) ?? modes[0],
);

function cycleView(): void {
  const index = modes.findIndex((mode) => mode.value === map.viewMode);
  const next = modes[(index + 1) % modes.length];
  if (next) map.setViewMode(next.value);
}
</script>

<template>
  <header
    class="relative z-40 flex h-16 shrink-0 items-center gap-3 border-b border-white/[0.07] bg-ink-950/75 px-3 backdrop-blur-xl sm:px-5"
  >
    <div class="flex min-w-0 items-center gap-3">
      <div class="seal h-9 w-9 shrink-0 rounded-[3px] text-[17px]">政</div>
      <div class="min-w-0">
        <div class="flex items-baseline gap-2">
          <h1 class="truncate font-display text-[13px] tracking-[0.06em] text-paper sm:text-[15px] sm:tracking-[0.08em]">
            中国政治人事 · 时空图谱
          </h1>
          <span class="hidden text-[9px] tracking-[0.18em] text-vermilion sm:inline">2012—</span>
        </div>
        <p class="mt-0.5 hidden truncate text-[9px] tracking-[0.16em] text-paper-faint sm:block">
          SPATIOTEMPORAL ARCHIVE OF CHINESE LEADERSHIP
        </p>
      </div>
    </div>

    <div class="ml-auto flex shrink-0 items-center gap-1.5">
      <span
        class="mr-1 hidden items-center gap-1.5 rounded-full border border-white/[0.08] bg-white/[0.02] px-2.5 py-1 text-[10px] text-paper-faint xl:inline-flex"
      >
        <span class="h-1.5 w-1.5 rounded-full bg-jade" />
        数据截至 <span class="tabular-nums text-paper-dim">{{ coverage }}</span>
      </span>

      <button
        class="group flex h-8 items-center gap-2 rounded-md border border-white/10 bg-white/[0.03] px-2.5 text-[11px] text-paper-faint transition hover:border-white/20 hover:text-paper sm:min-w-[150px]"
        aria-label="检索官员"
        @click="app.openSearch()"
      >
        <AppIcon name="search" :size="13" />
        <span class="hidden sm:inline">检索官员</span>
        <kbd class="ml-auto hidden rounded border border-white/10 bg-ink-800 px-1 py-px font-mono text-[9px] text-paper-faint sm:inline">
          /
        </kbd>
      </button>

      <button
        class="btn-ghost h-8"
        :class="app.directoryOpen ? 'border-vermilion/40 bg-vermilion/10 text-vermilion-bright' : ''"
        title="全国官员名册"
        @click="app.openDirectory()"
      >
        <AppIcon name="users" :size="13" />
        <span class="hidden lg:inline">名册</span>
      </button>

      <button
        class="btn-icon md:hidden"
        :title="`切换视图（当前：${currentMode.label}）`"
        :aria-label="`切换视图，当前${currentMode.label}`"
        @click="cycleView"
      >
        <AppIcon :name="currentMode.icon" :size="14" />
      </button>

      <div class="hidden items-center rounded-md border border-white/10 bg-white/[0.03] p-0.5 md:flex">
        <button
          v-for="mode in modes"
          :key="mode.value"
          class="flex h-7 items-center gap-1.5 rounded px-2 text-[10px] transition"
          :class="map.viewMode === mode.value
            ? 'bg-vermilion/90 text-white shadow-[0_2px_10px_-2px_rgba(200,73,47,.7)]'
            : 'text-paper-faint hover:bg-white/[0.06] hover:text-paper'"
          :title="`${mode.label}视图`"
          :aria-pressed="map.viewMode === mode.value"
          @click="map.setViewMode(mode.value)"
        >
          <AppIcon :name="mode.icon" :size="13" />
          <span class="hidden 2xl:inline">{{ mode.label }}</span>
        </button>
      </div>

      <button
        class="btn-icon hidden sm:inline-flex"
        title="系统说明 / 快捷键"
        aria-label="系统说明"
        @click="app.helpOpen = true"
      >
        <AppIcon name="info" :size="15" />
      </button>
    </div>
  </header>
</template>
