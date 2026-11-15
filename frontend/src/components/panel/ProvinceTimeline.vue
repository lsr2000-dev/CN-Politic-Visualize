<script setup lang="ts">
import { computed, ref, watch } from "vue";
import dayjs from "dayjs";
import { getRegionTimeline } from "@/api/client";
import { categoryColor, formatDate } from "@/utils/format";
import type { RegionTimelineResponse, RegionTimelineSpan } from "@/types";

const props = defineProps<{ regionCode: string }>();

const data = ref<RegionTimelineResponse | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);
let controller: AbortController | null = null;

async function load(): Promise<void> {
  controller?.abort();
  const current = new AbortController();
  controller = current;
  loading.value = true;
  error.value = null;
  try {
    data.value = await getRegionTimeline(props.regionCode, current.signal);
  } catch (caught) {
    if ((caught as Error).name === "CanceledError") return;
    error.value = caught instanceof Error ? caught.message : "席位更替加载失败";
  } finally {
    loading.value = false;
  }
}

watch(() => props.regionCode, load, { immediate: true });

const rangeStart = computed(() => dayjs(data.value?.from ?? "2012-11-08"));
const rangeEnd = computed(() => dayjs(data.value?.to ?? "2025-06-30"));
const totalDays = computed(() => Math.max(1, rangeEnd.value.diff(rangeStart.value, "day")));

const years = computed(() => {
  const ticks: Array<{ year: number; left: number }> = [];
  for (let year = rangeStart.value.year() + 1; year <= rangeEnd.value.year(); year += 1) {
    const day = dayjs(`${year}-01-01`);
    if (day.isAfter(rangeEnd.value)) continue;
    ticks.push({ year, left: (day.diff(rangeStart.value, "day") / totalDays.value) * 100 });
  }
  return ticks;
});

interface PositionedSpan extends RegionTimelineSpan {
  left: number;
  width: number;
}

const lanes = computed(() => {
  if (!data.value) return [];
  return data.value.lanes.map((lane) => ({
    ...lane,
    positioned: lane.spans.map<PositionedSpan>((span) => {
      const start = dayjs(span.start_date).isBefore(rangeStart.value)
        ? rangeStart.value
        : dayjs(span.start_date);
      const rawEnd = span.end_date ? dayjs(span.end_date) : rangeEnd.value;
      const end = rawEnd.isAfter(rangeEnd.value) ? rangeEnd.value : rawEnd;
      const days = Math.max(1, end.diff(start, "day") + 1);
      return {
        ...span,
        left: (Math.max(0, start.diff(rangeStart.value, "day")) / totalDays.value) * 100,
        width: (days / totalDays.value) * 100,
      };
    }),
  }));
});

function barStyle(span: PositionedSpan): Record<string, string> {
  const color = categoryColor(span.category);
  return {
    left: `${span.left}%`,
    width: `${Math.max(0.6, span.width)}%`,
    background: span.is_acting
      ? `repeating-linear-gradient(135deg, ${color}cc 0 4px, ${color}55 4px 8px)`
      : `linear-gradient(90deg, ${color}dd, ${color}88)`,
  };
}

const categoryLabels: Record<string, string> = {
  party: "党委",
  congress: "人大",
  government: "政府",
  cppcc: "政协",
  other: "其他",
};
</script>

<template>
  <section class="overflow-hidden rounded-xl border border-white/[0.07] bg-white/[0.015]">
    <div class="flex flex-wrap items-end justify-between gap-2 border-b border-white/[0.06] px-4 py-3">
      <div>
        <div class="label-eyebrow">SEAT TURNOVER</div>
        <h3 class="mt-1 font-display text-[15px] tracking-wide text-paper">四套班子席位更替</h3>
      </div>
      <span class="text-[9px] tabular-nums tracking-wider text-paper-faint">
        {{ formatDate(data?.from, "YYYY.MM") }} — {{ formatDate(data?.to, "YYYY.MM") }}
      </span>
    </div>

    <div v-if="loading" class="space-y-2 p-4">
      <div v-for="index in 4" :key="index" class="skeleton h-7 rounded" />
    </div>
    <div v-else-if="error" class="px-4 py-8 text-center text-[10px] text-vermilion-bright">
      {{ error }}
    </div>
    <div v-else-if="!lanes.length" class="px-4 py-8 text-center text-[10px] text-paper-faint">
      暂无席位更替记录
    </div>
    <div v-else class="overflow-x-auto p-4">
      <div class="min-w-[640px]">
        <div class="relative ml-[136px] h-5 border-b border-white/[0.05]">
          <div
            v-for="tick in years"
            :key="tick.year"
            class="absolute top-0 h-full border-l border-white/[0.06]"
            :style="{ left: `${tick.left}%` }"
          >
            <span class="absolute -top-0.5 left-1 text-[8px] tabular-nums text-paper-faint">{{ tick.year }}</span>
          </div>
        </div>

        <div
          v-for="lane in lanes"
          :key="lane.key"
          class="flex h-9 items-center border-b border-white/[0.03] last:border-0"
        >
          <div class="flex w-[136px] shrink-0 flex-col justify-center pr-2">
            <div class="flex items-center gap-1.5">
              <span class="h-2 w-[2px]" :style="{ backgroundColor: categoryColor(lane.category) }" />
              <span class="text-[9px] text-paper-dim">{{ categoryLabels[lane.category] ?? lane.category }}</span>
            </div>
            <span class="mt-0.5 truncate pl-3 text-[8px] text-paper-faint/80">{{ lane.title }}</span>
          </div>
          <div class="relative h-full flex-1">
            <div
              v-for="tick in years"
              :key="tick.year"
              class="pointer-events-none absolute inset-y-0 border-l border-white/[0.035]"
              :style="{ left: `${tick.left}%` }"
            />
            <div
              v-for="span in lane.positioned"
              :key="span.tenure_id"
              class="absolute top-1/2 flex h-[16px] -translate-y-1/2 cursor-default items-center overflow-hidden rounded-[2px] border border-white/10 text-[8px] text-white/95 transition hover:brightness-110"
              :style="barStyle(span)"
              :title="`${span.officer_name} · ${span.title} · ${formatDate(span.start_date, 'YYYY.MM')}—${formatDate(span.end_date, 'YYYY.MM')}`"
            >
              <span v-if="span.width > 6" class="truncate px-1">{{ span.officer_name }}</span>
            </div>
          </div>
        </div>
      </div>
      <p class="mt-2 text-[8px] text-paper-faint/60">斜纹为代理任职；悬停查看起止月份。</p>
    </div>
  </section>
</template>
