<script setup lang="ts">
import AppIcon from "../ui/AppIcon.vue";
import { useMapStore } from "@/stores/map";

const map = useMapStore();
</script>

<template>
  <div class="shrink-0 border-t border-white/[0.07] bg-ink-950/40 px-4 py-3">
    <div class="flex items-center justify-between gap-2">
      <div class="flex items-center gap-1.5 text-[10px] tracking-wide text-paper-faint">
        <AppIcon name="pin" :size="12" />
        <span>对比栏</span>
        <span class="tabular-nums text-paper-dim">{{ map.pinnedRegions.length }}/6</span>
      </div>
      <button
        class="inline-flex h-7 items-center gap-1.5 rounded-md border px-2.5 text-[10px] transition"
        :class="map.pinnedRegions.length >= 2
          ? 'border-vermilion/40 bg-vermilion/10 text-vermilion-bright hover:bg-vermilion/20'
          : 'cursor-not-allowed border-white/10 text-paper-faint/50'"
        :disabled="map.pinnedRegions.length < 2"
        @click="map.openCompare()"
      >
        <AppIcon name="compare" :size="11" />
        跨省对比
      </button>
    </div>

    <div class="mt-2 flex flex-wrap items-center gap-1.5">
      <button
        v-for="region in map.pinnedRegionObjects"
        :key="region.region_code"
        class="group inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] transition"
        :class="region.region_code === map.selectedRegionCode
          ? 'border-vermilion/45 bg-vermilion/10 text-paper'
          : 'border-white/10 bg-white/[0.03] text-paper-dim hover:border-white/20 hover:text-paper'"
        @click="map.selectRegion(region.region_code)"
      >
        {{ region.short_name }}
        <span
          class="ml-0.5 flex h-3 w-3 items-center justify-center rounded-full text-paper-faint opacity-60 transition hover:bg-white/10 hover:text-vermilion-bright group-hover:opacity-100"
          role="button"
          tabindex="0"
          :aria-label="`移除${region.short_name}`"
          @click.stop="map.removePin(region.region_code)"
          @keydown.enter.stop="map.removePin(region.region_code)"
        >
          <AppIcon name="close" :size="9" />
        </span>
      </button>
      <span v-if="!map.pinnedRegions.length" class="text-[10px] text-paper-faint/70">
        钉住当前省份，最多 6 个
      </span>
    </div>
  </div>
</template>
