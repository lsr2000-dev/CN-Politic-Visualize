<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { useMediaQuery } from "@vueuse/core";
import RegionDetail from "./panel/RegionDetail.vue";
import PanelEmpty from "./panel/PanelEmpty.vue";
import CentralTeamDetail from "./central/CentralTeamDetail.vue";
import CentralInstitutionDetail from "./central/CentralInstitutionDetail.vue";
import InstitutionDrawer from "./institution/InstitutionDrawer.vue";
import AppIcon from "./ui/AppIcon.vue";
import { useMapStore } from "@/stores/map";
import { useCentralStore } from "@/stores/central";
import { useTimelineStore } from "@/stores/timeline";
import { useDraggablePanel } from "@/composables/useDraggablePanel";

const map = useMapStore();
const central = useCentralStore();
const timeline = useTimelineStore();
const isDesktop = useMediaQuery("(min-width: 900px)");
const PANEL_MIN_WIDTH = 440;
const PANEL_MAX_WIDTH = 860;
const PANEL_DEFAULT_WIDTH = 560;
const PANEL_WIDTH_KEY = "polvis.sidebarWidth";

function initialPanelWidth(): number {
  const saved = Number(window.localStorage.getItem(PANEL_WIDTH_KEY));
  if (Number.isFinite(saved) && saved >= PANEL_MIN_WIDTH) {
    return Math.min(PANEL_MAX_WIDTH, saved);
  }
  return PANEL_DEFAULT_WIDTH;
}

const panelWidth = ref(initialPanelWidth());
const resizing = ref(false);
let resizeStartX = 0;
let resizeStartWidth = 0;

function startResize(event: PointerEvent): void {
  if (!isDesktop.value) return;
  event.preventDefault();
  resizing.value = true;
  resizeStartX = event.clientX;
  resizeStartWidth = panelWidth.value;
  window.addEventListener("pointermove", onResizeMove);
  window.addEventListener("pointerup", stopResize, { once: true });
}

function onResizeMove(event: PointerEvent): void {
  if (!resizing.value) return;
  const next = resizeStartWidth + (resizeStartX - event.clientX);
  panelWidth.value = Math.max(PANEL_MIN_WIDTH, Math.min(PANEL_MAX_WIDTH, next));
}

function stopResize(): void {
  if (!resizing.value) return;
  resizing.value = false;
  window.removeEventListener("pointermove", onResizeMove);
  window.localStorage.setItem(PANEL_WIDTH_KEY, String(panelWidth.value));
}

onBeforeUnmount(() => {
  window.removeEventListener("pointermove", onResizeMove);
});

const hasEntity = computed(() =>
  Boolean(map.selectedRegion || central.selectedTeam),
);

watch(
  () => map.selectedRegionCode,
  (code) => {
    if (code && (central.selectedTeam || central.selectedInstitution)) central.close();
  },
);

const { position, dragging, startDrag } = useDraggablePanel({
  width: PANEL_DEFAULT_WIDTH,
  offsetY: 80,
  margin: 16,
});

const floatingStyle = computed(() =>
  map.viewMode === "floating" && isDesktop.value
    ? {
        left: `${position.value.x}px`,
        top: `${position.value.y}px`,
        width: `${panelWidth.value}px`,
      }
    : undefined,
);

const panelStyle = computed(() =>
  map.viewMode === "fullscreen"
    ? undefined
    : { width: `${panelWidth.value}px`, maxWidth: "100vw" },
);

const rootClass = computed(() => {
  const base = "relative z-40 flex min-h-0 flex-col";
  if (map.viewMode === "sidebar") {
    return [
      base,
      "fixed bottom-0 right-0 top-16 border-l border-white/[0.07] bg-ink-900/95 shadow-panel backdrop-blur-xl",
      "lg:relative lg:inset-auto lg:z-20 lg:h-full lg:shrink-0 lg:bg-ink-900/35 lg:shadow-none",
      hasEntity.value ? "flex" : "hidden lg:flex",
    ];
  }
  if (map.viewMode === "floating") {
    return [
      base,
      "fixed max-h-[calc(100vh-11rem)] overflow-hidden rounded-xl border border-white/10 bg-ink-900/95 shadow-panel backdrop-blur-2xl",
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
  if (central.selectedTeam) {
    central.close();
    return;
  }
  map.selectRegion(null);
}

function closeInstitution(): void {
  central.selectInstitution(null, timeline.currentDate);
}
</script>

<template>
  <aside :class="rootClass" :style="[floatingStyle, panelStyle]" aria-label="省份人事详情面板">
    <div
      v-if="map.viewMode === 'sidebar' && isDesktop"
      class="panel-resize-handle"
      :class="resizing ? 'panel-resize-handle--active' : ''"
      title="拖动调整侧栏宽度"
      @pointerdown="startResize"
    />
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
      <CentralTeamDetail v-if="central.selectedTeam" @close="closePanel" />
      <RegionDetail v-else :mode="map.viewMode" @close="closePanel">
        <template #empty>
          <PanelEmpty />
        </template>
      </RegionDetail>
    </div>
  </aside>

  <InstitutionDrawer :open="Boolean(central.selectedInstitution)" @close="closeInstitution">
    <CentralInstitutionDetail
      v-if="central.selectedInstitution"
      @close="closeInstitution"
    />
  </InstitutionDrawer>
</template>

<style scoped>
.panel-resize-handle {
  position: absolute;
  left: -4px;
  top: 0;
  bottom: 0;
  z-index: 60;
  width: 8px;
  cursor: col-resize;
  touch-action: none;
}
.panel-resize-handle::after {
  content: "";
  position: absolute;
  left: 3px;
  top: 16px;
  bottom: 16px;
  width: 2px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  transition: background 0.15s ease;
}
.panel-resize-handle:hover::after,
.panel-resize-handle--active::after {
  background: rgba(176, 138, 74, 0.7);
}
</style>
