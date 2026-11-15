<script setup lang="ts">
import AppIcon from "../ui/AppIcon.vue";
import { useMapStore } from "@/stores/map";
import { useTimelineStore } from "@/stores/timeline";
import { formatDate } from "@/utils/format";

const map = useMapStore();
const timeline = useTimelineStore();
</script>

<template>
  <div class="flex h-full flex-col items-center justify-center px-8 text-center">
    <div class="relative">
      <div class="seal h-12 w-12 rounded-sm text-xl opacity-90">图</div>
      <span class="absolute -right-2 -top-2 h-3 w-3 rounded-full border border-ink-900 bg-gold/80" />
    </div>
    <p class="mt-5 font-display text-lg tracking-wide text-paper">选择一个省份</p>
    <p class="mt-2 max-w-[260px] text-[11px] leading-relaxed text-paper-faint">
      点击地图上的省级行政区，查看 {{ formatDate(timeline.currentDate, "YYYY 年 MM 月 DD 日") }}
      时点的四套班子主官与个人履历。
    </p>

    <div class="mt-6 w-full max-w-[300px] rounded-lg border border-white/[0.07] bg-white/[0.02] p-3">
      <div class="label-eyebrow text-left">已钉住 / PINNED</div>
      <div v-if="map.pinnedRegionObjects.length" class="mt-2 space-y-1">
        <button
          v-for="region in map.pinnedRegionObjects"
          :key="region.region_code"
          class="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left transition hover:bg-white/[0.05]"
          @click="map.selectRegion(region.region_code)"
        >
          <span class="h-1.5 w-1.5 rounded-full bg-vermilion" />
          <span class="text-[12px] text-paper">{{ region.region_name }}</span>
          <span class="ml-auto text-[10px] text-paper-faint">
            {{ region.teams.party.members[0]?.officer.name ?? "—" }}
          </span>
        </button>
      </div>
      <p v-else class="mt-2 text-left text-[10px] text-paper-faint">暂无钉住的省份</p>
    </div>

    <div class="mt-5 flex items-center gap-1.5 text-[10px] text-paper-faint/70">
      <AppIcon name="map-pin" :size="11" />
      支持 31 个省级行政区 · 可下探地级市（接口预留）
    </div>
  </div>
</template>
