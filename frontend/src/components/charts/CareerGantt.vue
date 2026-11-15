<script setup lang="ts">
import { computed, ref } from "vue";
import dayjs from "dayjs";
import { categoryColor, clamp, formatDate, formatDuration } from "@/utils/format";
import type { CareerLane, CareerResponse, CareerSpan } from "@/types";

const props = defineProps<{ career: CareerResponse }>();

const chart = ref<HTMLElement | null>(null);
const hovered = ref<{ span: CareerSpan; x: number; y: number } | null>(null);
const focused = ref<CareerSpan | null>(null);

const rangeStart = computed(() => dayjs(props.career.range.from));
const rangeEnd = computed(() => dayjs(props.career.range.to));
const totalDays = computed(() => Math.max(1, rangeEnd.value.diff(rangeStart.value, "day")));

interface PositionedSpan extends CareerSpan {
  left: number;
  width: number;
  row: number;
  clippedEnd: string;
  clippedDays: number;
}

interface PositionedLane extends CareerLane {
  positioned: PositionedSpan[];
  height: number;
}

const lanes = computed<PositionedLane[]>(() => {
  return props.career.lanes.map((lane) => {
    const sorted = [...lane.spans].sort(
      (a, b) => dayjs(a.start_date).valueOf() - dayjs(b.start_date).valueOf(),
    );
    const rowEnds: number[] = [];
    const positioned: PositionedSpan[] = sorted.map((span) => {
      const start = dayjs(span.start_date).isBefore(rangeStart.value)
        ? rangeStart.value
        : dayjs(span.start_date);
      const rawEnd = span.end_date ? dayjs(span.end_date) : rangeEnd.value;
      const end = rawEnd.isAfter(rangeEnd.value) ? rangeEnd.value : rawEnd;
      const startOffset = Math.max(0, start.diff(rangeStart.value, "day"));
      const days = Math.max(1, end.diff(start, "day") + 1);
      const left = (startOffset / totalDays.value) * 100;
      const width = Math.max(0.7, (days / totalDays.value) * 100);
      let row = rowEnds.findIndex((value) => value < startOffset);
      if (row < 0) {
        row = rowEnds.length;
        rowEnds.push(startOffset + days);
      } else {
        rowEnds[row] = startOffset + days;
      }
      return {
        ...span,
        left,
        width,
        row,
        clippedEnd: end.format("YYYY-MM-DD"),
        clippedDays: days,
      };
    });
    const rows = Math.max(1, ...positioned.map((span) => span.row + 1));
    return { ...lane, positioned, height: rows * 28 + 8 };
  });
});

const years = computed(() => {
  const ticks: Array<{ year: number; left: number }> = [];
  for (let year = rangeStart.value.year() + 1; year <= rangeEnd.value.year(); year += 1) {
    const day = dayjs(`${year}-01-01`);
    if (day.isAfter(rangeEnd.value)) continue;
    ticks.push({ year, left: (day.diff(rangeStart.value, "day") / totalDays.value) * 100 });
  }
  return ticks;
});

const cutoff = computed(() => {
  const end = dayjs(props.career.range.coverage_end);
  if (end.isAfter(rangeEnd.value)) return null;
  return (end.diff(rangeStart.value, "day") / totalDays.value) * 100;
});

const tooltipStyle = computed(() => {
  if (!hovered.value || !chart.value) return {};
  const width = 268;
  const rect = chart.value.getBoundingClientRect();
  const x = clamp(hovered.value.x + 14, 8, Math.max(8, rect.width - width - 8));
  const top = hovered.value.y + 18;
  const flip = top + 160 > rect.height;
  return {
    left: `${x}px`,
    top: flip ? `${Math.max(8, hovered.value.y - 150)}px` : `${top}px`,
    width: `${width}px`,
  };
});

function onEnter(event: MouseEvent, span: CareerSpan): void {
  updateHover(event, span);
}

function updateHover(event: MouseEvent, span: CareerSpan): void {
  if (!chart.value) return;
  const rect = chart.value.getBoundingClientRect();
  hovered.value = {
    span,
    x: event.clientX - rect.left,
    y: event.clientY - rect.top,
  };
}

function barStyle(span: PositionedSpan): Record<string, string> {
  const color = categoryColor(span.category);
  const background = span.is_acting
    ? `repeating-linear-gradient(135deg, ${color}cc 0 5px, ${color}66 5px 10px)`
    : `linear-gradient(90deg, ${color}dd, ${color}99)`;
  return {
    left: `${span.left}%`,
    width: `${span.width}%`,
    top: `${span.row * 28 + 4}px`,
    background,
    borderColor: span.is_concurrent ? `${color}` : "rgba(255,255,255,0.14)",
  };
}

function selectSpan(span: CareerSpan): void {
  focused.value = focused.value?.tenure_id === span.tenure_id ? null : span;
}
</script>

<template>
  <div class="overflow-x-auto">
    <div ref="chart" class="relative min-w-[620px]" @mouseleave="hovered = null">
      <!-- axis -->
      <div class="relative ml-[88px] h-7 border-b border-white/[0.06]">
        <div
          v-for="tick in years"
          :key="tick.year"
          class="absolute top-0 h-full border-l border-white/[0.06]"
          :style="{ left: `${tick.left}%` }"
        >
          <span class="absolute -top-0.5 left-1 text-[9px] tabular-nums text-paper-faint">
            {{ tick.year }}
          </span>
        </div>
        <div
          v-if="cutoff !== null"
          class="absolute top-0 h-full border-l border-dashed border-gold/50"
          :style="{ left: `${cutoff}%` }"
        >
          <span class="absolute -top-0.5 left-1 whitespace-nowrap text-[8px] tracking-widest text-gold/80">
            数据截至
          </span>
        </div>
      </div>

      <!-- lanes -->
      <div class="relative">
        <div
          v-for="lane in lanes"
          :key="lane.key"
          class="group/lane flex border-b border-white/[0.04] last:border-0"
          :style="{ height: `${lane.height}px` }"
        >
          <div class="flex w-[88px] shrink-0 flex-col justify-center border-r border-white/[0.05] pr-2">
            <span class="truncate text-[10px] text-paper-dim">{{ lane.label }}</span>
            <span class="mt-0.5 truncate text-[8px] tracking-wide text-paper-faint/60">
              {{ lane.key === "central" ? "CENTRAL" : lane.key }}
            </span>
          </div>
          <div class="relative flex-1">
            <!-- year grid -->
            <div
              v-for="tick in years"
              :key="tick.year"
              class="pointer-events-none absolute inset-y-0 border-l border-white/[0.04]"
              :style="{ left: `${tick.left}%` }"
            />
            <div
              v-for="span in lane.positioned"
              :key="span.tenure_id"
              class="absolute flex h-[22px] cursor-pointer items-center overflow-hidden rounded-[3px] border text-[9px] text-white/95 shadow-sm transition-[filter,transform] duration-200 hover:z-10 hover:brightness-110"
              :class="focused?.tenure_id === span.tenure_id ? 'z-10 ring-1 ring-white/60' : ''"
              :style="barStyle(span)"
              :title="`${span.title} · ${formatDate(span.start_date, 'YYYY.MM')}—${formatDate(span.end_date, 'YYYY.MM')}`"
              @mouseenter="onEnter($event, span)"
              @mousemove="updateHover($event, span)"
              @click="selectSpan(span)"
            >
              <span v-if="span.width > 13" class="truncate px-1.5">
                {{ span.title }}
              </span>
              <span
                v-if="span.width > 24"
                class="ml-auto shrink-0 pr-1.5 text-[8px] tabular-nums text-white/70"
              >
                <template v-if="span.start_precision === 'snapshot' && span.duration_days > 0">约 {{ formatDuration(span.duration_days) }}</template>
                <template v-else-if="span.start_precision === 'snapshot'">现任</template>
                <template v-else>{{ formatDuration(span.duration_days) }}</template>
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- tooltip -->
      <Transition name="fade">
        <div
          v-if="hovered"
          class="pointer-events-none absolute z-30 rounded-lg border border-white/15 bg-ink-950/95 p-3 shadow-panel"
          :style="tooltipStyle"
        >
          <div class="flex items-start justify-between gap-2">
            <span class="font-display text-[13px] leading-tight text-paper">
              {{ hovered.span.title }}
            </span>
            <span
              v-if="hovered.span.is_acting"
              class="shrink-0 rounded border border-vermilion/40 px-1 py-px text-[8px] text-vermilion-bright"
            >
              代理
            </span>
          </div>
          <div class="mt-1.5 space-y-0.5 text-[10px] text-paper-faint">
            <div>{{ hovered.span.officer_name }}</div>
            <div class="tabular-nums">
              {{ formatDate(hovered.span.start_date, "YYYY.MM.DD") }} —
              {{ hovered.span.end_date ? formatDate(hovered.span.end_date, "YYYY.MM.DD") : "至今" }}
              <span class="text-paper-dim">
                · {{ hovered.span.start_precision === "snapshot"
                  ? (hovered.span.duration_days > 0 ? `约 ${formatDuration(hovered.span.duration_days)}` : "现任（起始待考）")
                  : formatDuration(hovered.span.duration_days) }}
              </span>
            </div>
            <div v-if="hovered.span.is_concurrent" class="text-gold/80">兼任职务</div>
          </div>
          <div class="mt-2 border-t border-white/10 pt-1.5 text-[8px] tracking-widest text-paper-faint/60">
            点击查看任职详情
          </div>
        </div>
      </Transition>
    </div>

    <!-- focused detail -->
    <Transition name="fade">
      <div
        v-if="focused"
        class="mx-1 mt-2 flex items-center gap-3 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2"
      >
        <span class="h-2 w-2 shrink-0" :style="{ backgroundColor: categoryColor(focused.category) }" />
        <div class="min-w-0 flex-1">
          <div class="truncate text-[11px] text-paper">{{ focused.title }}</div>
          <div class="mt-0.5 text-[9px] tabular-nums text-paper-faint">
            {{ formatDate(focused.start_date, "YYYY.MM.DD") }} —
            {{ focused.end_date ? formatDate(focused.end_date, "YYYY.MM.DD") : "至今" }}
            · {{ formatDuration(focused.duration_days) }}
            <template v-if="focused.org_name"> · {{ focused.org_name }}</template>
          </div>
        </div>
        <span v-if="focused.is_acting" class="rounded border border-vermilion/35 px-1 py-px text-[8px] text-vermilion-bright">
          代理
        </span>
      </div>
    </Transition>
  </div>
</template>
