<script setup lang="ts">
import { computed } from "vue";
import ChinaMap from "./ChinaMap.vue";
import MapLegend from "./MapLegend.vue";
import CentralBlock from "./central/CentralBlock.vue";
import AppIcon from "./ui/AppIcon.vue";
import { useAppStore } from "@/stores/app";
import { useMapStore } from "@/stores/map";
import { useTimelineStore } from "@/stores/timeline";
import { formatDate } from "@/utils/format";

const app = useAppStore();
const map = useMapStore();
const timeline = useTimelineStore();

const snapshotDate = computed(() => formatDate(map.snapshot?.as_of ?? timeline.currentDate, "YYYY 年 MM 月 DD 日"));
const hovering = computed(() => map.hoveredRegion);
</script>

<template>
  <div class="relative h-full w-full overflow-hidden bg-ink-950">
    <!-- atmosphere -->
    <div class="pointer-events-none absolute inset-0 bg-grid-faint bg-grid opacity-[0.35]" />
    <div class="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_60%_55%_at_52%_46%,rgba(58,86,101,0.18),transparent_70%)]" />
    <div class="pointer-events-none absolute inset-x-0 bottom-0 h-52 bg-gradient-to-t from-ink-950 via-ink-950/70 to-transparent" />

    <ChinaMap
      v-if="app.geo"
      :geo="app.geo"
      class="absolute inset-x-0 top-0 bottom-[104px]"
    />

    <!-- central leadership block -->
    <div class="pointer-events-auto absolute left-5 top-[108px] z-20 max-md:left-2 max-md:top-[96px] max-md:origin-top-left max-md:scale-90">
      <CentralBlock />
    </div>

    <!-- loading shimmer -->
    <div
      v-if="map.loading"
      class="pointer-events-none absolute inset-x-0 top-0 z-30 h-[2px] overflow-hidden bg-white/5"
    >
      <div class="h-full w-1/3 animate-[shimmer_1.4s_infinite_linear] bg-gradient-to-r from-transparent via-vermilion to-transparent" />
    </div>

    <!-- title -->
    <div class="pointer-events-none absolute left-6 top-5 z-10 max-w-[360px]">
      <div class="flex items-center gap-2">
        <span class="h-3 w-[2px] bg-vermilion" />
        <span class="label-eyebrow">CHINA / CENTRAL & LOCAL LEADERSHIP</span>
      </div>
      <h2 class="mt-2 font-display text-[26px] leading-tight tracking-wide text-paper text-shadow">
        中央与地方领导班子时空切片
      </h2>
      <p class="mt-1.5 text-[11px] leading-relaxed text-paper-faint">
        {{ snapshotDate }} · 拖拽时间轴或点击省份、中央机构下探
      </p>
    </div>

    <!-- stats -->
    <div class="absolute right-5 top-5 z-10 hidden items-stretch gap-px overflow-hidden rounded-lg border border-white/10 bg-ink-900/70 backdrop-blur-md lg:flex">
      <div class="px-3 py-2">
        <div class="label-eyebrow">省级</div>
        <div class="font-display text-lg leading-tight text-paper tabular-nums">
          {{ map.snapshot?.stats.region_count ?? 31 }}
        </div>
      </div>
      <div class="w-px bg-white/10" />
      <div class="px-3 py-2">
        <div class="label-eyebrow">在任</div>
        <div class="font-display text-lg leading-tight text-paper tabular-nums">
          {{ map.snapshot?.stats.member_count ?? "—" }}
        </div>
      </div>
      <div class="w-px bg-white/10" />
      <div class="px-3 py-2">
        <div class="label-eyebrow">代理</div>
        <div class="font-display text-lg leading-tight text-vermilion-bright tabular-nums">
          {{ map.snapshot?.stats.acting_count ?? 0 }}
        </div>
      </div>
    </div>

    <!-- hovered province -->
    <Transition name="fade">
      <div
        v-if="hovering"
        class="pointer-events-none absolute right-5 top-[86px] z-10 hidden w-[190px] rounded-lg border border-white/10 bg-ink-900/80 p-3 backdrop-blur-md lg:block"
      >
        <div class="flex items-baseline justify-between">
          <span class="font-display text-sm text-paper">{{ hovering.region_name }}</span>
          <span class="text-[9px] tracking-widest text-paper-faint">{{ hovering.region_code }}</span>
        </div>
        <div class="mt-2 space-y-1 text-[11px]">
          <div class="flex justify-between gap-2">
            <span class="text-paper-faint">书记</span>
            <span class="truncate text-paper-dim">{{ hovering.teams.party.members[0]?.officer.name ?? "未收录" }}</span>
          </div>
          <div class="flex justify-between gap-2">
            <span class="text-paper-faint">省长</span>
            <span class="truncate text-paper-dim">{{ hovering.teams.government.members[0]?.officer.name ?? "未收录" }}</span>
          </div>
        </div>
      </div>
    </Transition>

    <!-- legend -->
    <div class="absolute bottom-[122px] left-5 z-10">
      <MapLegend />
    </div>

    <!-- hint -->
    <div class="pointer-events-none absolute bottom-[126px] right-5 z-10 hidden flex-col items-end gap-1.5 text-right md:flex">
      <span class="chip">
        <span class="h-1 w-1 rounded-full bg-jade" />
        数据截至 {{ formatDate(map.snapshot?.coverage.coverage_end ?? timeline.coverageEnd, "YYYY.MM.DD") }}
      </span>
      <span class="text-[10px] text-paper-faint">滚轮缩放 · 拖拽平移 · 点击省份</span>
    </div>

    <!-- error -->
    <div
      v-if="map.error"
      class="absolute inset-0 z-20 flex items-center justify-center bg-ink-950/60 backdrop-blur-sm"
    >
      <div class="w-[320px] rounded-xl border border-vermilion/25 bg-ink-900/90 p-5 text-center shadow-panel">
        <AppIcon name="info" :size="22" class="mx-auto text-vermilion-bright" />
        <p class="mt-3 text-sm text-paper">地图数据加载失败</p>
        <p class="mt-1 text-[11px] leading-relaxed text-paper-faint">{{ map.error }}</p>
        <button class="btn-ghost mt-4" @click="map.loadSnapshot(timeline.currentDate, true)">
          <AppIcon name="refresh" :size="13" /> 重试
        </button>
      </div>
    </div>
  </div>
</template>
