<script setup lang="ts">
import { computed, watch } from "vue";
import { useMediaQuery } from "@vueuse/core";
import RegionDetail from "./panel/RegionDetail.vue";
import PanelEmpty from "./panel/PanelEmpty.vue";
import CentralTeamDetail from "./central/CentralTeamDetail.vue";
import CentralInstitutionDetail from "./central/CentralInstitutionDetail.vue";
import AppIcon from "./ui/AppIcon.vue";
import { useMapStore } from "@/stores/map";
import { useCentralStore } from "@/stores/central";
import { useTimelineStore } from "@/stores/timeline";
import { useDraggablePanel } from "@/composables/useDraggablePanel";

const map = useMapStore();
const central = useCentralStore();
const timeline = useTimelineStore();
const isDesktop = useMediaQuery("(min-width: 900px)");
const panelWidth = 460;

const hasEntity = computed(() =>
  Boolean(map.selectedRegion || central.selectedInstitution || central.selectedTeam),
);

watch(
  () => map.selectedRegionCode,
  (code) => {
    if (code && (central.selectedTeam || central.selectedInstitution)) central.close();
  },
);

const { position, dragging, startDrag } = useDraggablePanel({
  width: panelWidth,
  offsetY: 80,
  margin: 16,
});

const floatingStyle = computed(() =>
  map.viewMode === "floating" && isDesktop.value
    ? {
        left: `${position.value.x}px`,
        top: `${position.value.y}px`,
        width: `${panelWidth}px`,
      }
    : undefined,
);

const rootClass = computed(() => {
  const base = "z-40 flex min-h-0 flex-col";
  if (map.viewMode === "sidebar") {
    return [
      base,
      "fixed bottom-0 right-0 top-16 w-[min(100vw,440px)] border-l border-white/[0.07] bg-ink-900/95 shadow-panel backdrop-blur-xl",
      "lg:relative lg:inset-auto lg:z-20 lg:h-full lg:w-[432px] lg:shrink-0 lg:bg-ink-900/35 lg:shadow-none",
      hasEntity.value ? "flex" : "hidden lg:flex",
    ];
  }
  if (map.viewMode === "floating") {
    return [
      base,
      "fixed max-h-[calc(100vh-11rem)] w-[460px] overflow-hidden rounded-xl border border-white/10 bg-ink-900/95 shadow-panel backdrop-blur-2xl",
      "max-lg:inset-x-0 max-lg:bottom-0 max-lg:top-auto max-lg:max-h-[78vh] max-lg:w-full max-lg:rounded-t-2xl max-lg:pb-[env(safe-area-inset-bottom)]",
    ];
  }
  return [
    base,
    "fixed inset-x-0 bottom-0 top-16 z-30 bg-ink-950/95 backdrop-blur-2xl",
  ];
});

function closePanel(): void {
  if (map.viewMode === "fullscreen") map.setViewMode("sidebar");
  if (central.selectedInstitution) {
    central.selectInstitution(null, timeline.currentDate);
    return;
  }
  if (central.selectedTeam) {
    central.close();
    return;
  }
  map.selectRegion(null);
}
</script>

<template>
  <aside :class="rootClass" :style="floatingStyle" aria-label="省份人事详情面板">
    <!-- floating drag handle -->
    <div
      v-if="map.viewMode === 'floating' && isDesktop"
      class="flex shrink-0 cursor-grab items-center gap-2 border-b border-white/[0.06] px-4 py-2 active:cursor-grabbing"
      :class="dragging ? 'bg-white/[0.03]' : ''"
      @pointerdown="startDrag"
    >
      <div class="flex gap-[3px]">
        <span v-for="dot in 3" :key="dot" class="h-[3px] w-[3px] rounded-full bg-paper-faint/60" />
      </div>
      <span class="text-[9px] tracking-[0.22em] text-paper-faint">FLOATING · 拖动移动</span>
      <button
        class="btn-icon ml-auto h-6 w-6"
        data-no-drag
        title="收起为侧边栏"
        @click="map.setViewMode('sidebar')"
      >
        <AppIcon name="panel" :size="12" />
      </button>
      <button
        class="btn-icon h-6 w-6"
        data-no-drag
        title="关闭"
        @click="closePanel"
      >
        <AppIcon name="close" :size="12" />
      </button>
    </div>

    <!-- fullscreen chrome -->
    <div
      v-if="map.viewMode === 'fullscreen'"
      class="flex shrink-0 items-center justify-between border-b border-white/10 px-6 py-2"
    >
      <div class="flex items-center gap-2">
        <span class="h-1.5 w-1.5 rounded-full bg-vermilion live-dot" />
        <span class="label-eyebrow">IMMERSIVE VIEW / 全屏沉浸浏览</span>
      </div>
      <div class="flex items-center gap-2">
        <span class="hidden text-[10px] text-paper-faint md:inline">Esc 退出 · 点击官员查看履历</span>
        <button class="btn-ghost h-7" @click="map.setViewMode('sidebar')">
          <AppIcon name="panel" :size="12" /> 退出全屏
        </button>
      </div>
    </div>

    <div
      class="min-h-0 flex-1"
      :class="map.viewMode === 'fullscreen' ? 'mx-auto w-full max-w-[1500px]' : ''"
    >
      <CentralInstitutionDetail v-if="central.selectedInstitution" @close="closePanel" />
      <CentralTeamDetail v-else-if="central.selectedTeam" @close="closePanel" />
      <RegionDetail v-else :mode="map.viewMode" @close="closePanel">
        <template #empty>
          <PanelEmpty />
        </template>
      </RegionDetail>
    </div>
  </aside>
</template>
