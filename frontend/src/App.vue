<script setup lang="ts">
import { onMounted, watch } from "vue";
import { useDebounceFn } from "@vueuse/core";
import AppHeader from "./components/AppHeader.vue";
import MapStage from "./components/MapStage.vue";
import TimelineScrubber from "./components/TimelineScrubber.vue";
import DetailPanel from "./components/DetailPanel.vue";
import SearchPalette from "./components/SearchPalette.vue";
import HelpDialog from "./components/HelpDialog.vue";
import OfficerDrawer from "./components/OfficerDrawer.vue";
import SeatDrawer from "./components/SeatDrawer.vue";
import CompareOverlay from "./components/CompareOverlay.vue";
import DirectoryView from "./components/DirectoryView.vue";
import CentralPinnedBar from "./components/central/CentralPinnedBar.vue";
import { useAppStore, useOfficerStore } from "./stores/app";
import { useTimelineStore } from "./stores/timeline";
import { useSnapshotSync } from "./composables/useSnapshotSync";
import { useKeyboardShortcuts } from "./composables/useKeyboardShortcuts";
import { useUrlState } from "./composables/useUrlState";

const app = useAppStore();
const timeline = useTimelineStore();
const officer = useOfficerStore();

useSnapshotSync();
useKeyboardShortcuts();
useUrlState();

const refreshProfile = useDebounceFn((date: string) => {
  if (officer.activeOfficerId !== null) void officer.refreshProfile(date);
}, 620);

const refreshSeat = useDebounceFn((date: string) => {
  if (officer.activeSeat) {
    void officer.openSeat(officer.activeSeat, date);
  }
}, 620);

watch(
  () => timeline.currentDate,
  (date) => {
    refreshProfile(date);
    refreshSeat(date);
  },
);

onMounted(() => {
  void app.bootstrap();
});

function retry(): void {
  app.ready = false;
  app.bootError = null;
  void app.bootstrap();
}
</script>

<template>
  <div class="flex h-full flex-col">
    <AppHeader />

    <main class="relative flex min-h-0 flex-1">
      <section class="relative min-w-0 flex-1">
        <MapStage />
        <TimelineScrubber />
      </section>
      <DetailPanel />
    <CentralPinnedBar />
    </main>

    <SearchPalette />
    <HelpDialog />
    <DirectoryView v-if="app.directoryOpen" />
    <OfficerDrawer />
    <SeatDrawer />
    <CompareOverlay />

    <Transition name="fade">
      <div
        v-if="!app.ready"
        class="fixed inset-0 z-[90] flex flex-col items-center justify-center overflow-hidden bg-ink-950"
      >
        <div class="pointer-events-none absolute inset-0 bg-grid-faint bg-grid opacity-[0.3]" />
        <div class="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_50%_40%_at_50%_45%,rgba(200,73,47,.12),transparent_70%)]" />
        <div class="noise absolute inset-0" />

        <div class="relative flex flex-col items-center px-6 text-center">
          <div class="seal h-16 w-16 rounded-sm text-[30px]">政</div>
          <div class="mt-5 flex items-center gap-2">
            <span class="h-px w-6 bg-vermilion/60" />
            <span class="label-eyebrow">SPATIOTEMPORAL ARCHIVE</span>
            <span class="h-px w-6 bg-vermilion/60" />
          </div>
          <h1 class="mt-3 font-display text-[26px] tracking-[0.16em] text-paper">地方政治人事 · 时空图谱</h1>
          <p class="mt-2 text-[10px] tracking-[0.2em] text-paper-faint">2012 年 11 月 —— 至今 · 31 个省级行政区</p>

          <div v-if="app.bootError" class="mt-8 w-[360px] max-w-full rounded-xl border border-vermilion/25 bg-ink-900/80 p-5 text-left">
            <div class="flex items-center gap-2 text-[12px] text-paper">
              <span class="h-1.5 w-1.5 rounded-full bg-vermilion" />
              无法连接数据服务
            </div>
            <p class="mt-2 break-words text-[10px] leading-relaxed text-paper-faint">{{ app.bootError }}</p>
            <p class="mt-2 text-[9px] leading-relaxed text-paper-faint/70">
              请确认 FastAPI 已启动：<code class="rounded bg-white/5 px-1 py-0.5 font-mono">uvicorn app.main:app --reload</code>
            </p>
            <button class="btn-ghost mt-4 w-full justify-center" @click="retry">
              重新连接
            </button>
          </div>

          <div v-else class="mt-8 flex flex-col items-center gap-3">
            <div class="flex items-center gap-1.5">
              <span
                v-for="index in 3"
                :key="index"
                class="h-1 w-1 rounded-full bg-vermilion"
                :style="{ animation: `pulse-dot 1.4s ${index * 0.18}s infinite ease-in-out` }"
              />
            </div>
            <p class="text-[10px] tracking-[0.18em] text-paper-faint">正在装载时空档案</p>
          </div>
        </div>

        <div class="absolute bottom-6 flex items-center gap-3 text-[9px] tracking-[0.16em] text-paper-faint/60">
          <span>VUE 3</span><span class="h-2 w-px bg-white/15" />
          <span>FASTAPI</span><span class="h-2 w-px bg-white/15" />
          <span>POSTGRESQL / POSTGIS</span><span class="h-2 w-px bg-white/15" />
          <span>ECHARTS</span>
        </div>
      </div>
    </Transition>
  </div>
</template>
