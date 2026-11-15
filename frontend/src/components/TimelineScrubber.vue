<script setup lang="ts">
import { computed, ref } from "vue";
import { useMediaQuery } from "@vueuse/core";
import dayjs from "dayjs";
import AppIcon from "./ui/AppIcon.vue";
import { useTimelineStore } from "@/stores/timeline";
import { clamp, formatDate } from "@/utils/format";

const timeline = useTimelineStore();
const track = ref<HTMLDivElement | null>(null);
const dragging = ref(false);
const hoverRatio = ref<number | null>(null);
const wide = useMediaQuery("(min-width: 640px)");

const weekday = computed(() => {
  return ["周日", "周一", "周二", "周三", "周四", "周五", "周六"][dayjs(timeline.currentDate).day()];
});

const yearTicks = computed(() => {
  const start = dayjs(timeline.rangeStart);
  const end = dayjs(timeline.rangeEnd);
  const ticks: Array<{ year: number; ratio: number }> = [];
  for (let year = start.year() + 1; year <= end.year(); year += 1) {
    const day = dayjs(`${year}-01-01`);
    if (day.isAfter(end)) continue;
    if (!wide.value && year % 2 !== 0) continue;
    ticks.push({
      year,
      ratio: day.diff(start, "day") / timeline.totalDays,
    });
  }
  return ticks;
});

const hoverDate = computed(() => {
  if (hoverRatio.value === null) return null;
  return dayjs(timeline.rangeStart)
    .add(Math.round(hoverRatio.value * timeline.totalDays), "day")
    .format("YYYY.MM.DD");
});

function ratioFromEvent(event: PointerEvent): number {
  if (!track.value) return 0;
  const rect = track.value.getBoundingClientRect();
  return clamp((event.clientX - rect.left) / rect.width, 0, 1);
}

function applyRatio(ratio: number): void {
  const day = dayjs(timeline.rangeStart)
    .add(Math.round(ratio * timeline.totalDays), "day")
    .format("YYYY-MM-DD");
  timeline.setDate(day);
}

function onPointerDown(event: PointerEvent): void {
  if (event.button !== 0) return;
  dragging.value = true;
  timeline.setScrubbing(true);
  (event.currentTarget as HTMLElement).setPointerCapture?.(event.pointerId);
  applyRatio(ratioFromEvent(event));
}

function onPointerMove(event: PointerEvent): void {
  const ratio = ratioFromEvent(event);
  hoverRatio.value = ratio;
  if (dragging.value) applyRatio(ratio);
}

function onPointerUp(event: PointerEvent): void {
  if (!dragging.value) return;
  dragging.value = false;
  timeline.setScrubbing(false);
  (event.currentTarget as HTMLElement).releasePointerCapture?.(event.pointerId);
}

function onPointerLeave(): void {
  if (!dragging.value) hoverRatio.value = null;
}

function cycleSpeed(): void {
  const options = [1, 2, 4];
  const index = options.indexOf(timeline.playbackSpeed);
  timeline.setPlaybackSpeed(options[(index + 1) % options.length] ?? 1);
}
</script>

<template>
  <div
    class="absolute inset-x-0 bottom-0 z-20 select-none border-t border-white/[0.07] bg-gradient-to-t from-ink-950 via-ink-950/95 to-ink-950/55 backdrop-blur-xl"
  >
    <!-- control row -->
    <div class="flex items-center gap-3 px-5 pb-1 pt-3">
      <button
        class="group flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-vermilion text-white shadow-seal transition hover:bg-vermilion-bright"
        :aria-label="timeline.isPlaying ? '暂停时间轴' : '播放时间轴'"
        @click="timeline.togglePlay()"
      >
        <AppIcon :name="timeline.isPlaying ? 'pause' : 'play'" :size="15" />
      </button>

      <div class="min-w-0">
        <div class="flex items-baseline gap-2">
          <span class="font-display text-[19px] leading-none tracking-wide text-paper tabular-nums">
            {{ formatDate(timeline.currentDate, "YYYY 年 MM 月 DD 日") }}
          </span>
          <span class="hidden text-[10px] tracking-widest text-paper-faint sm:inline">{{ weekday }}</span>
        </div>
        <div class="mt-1 flex items-center gap-1.5 text-[10px] text-paper-faint">
          <span>十八大以来</span>
          <span class="h-2.5 w-px bg-white/15" />
          <span class="tabular-nums">{{ timeline.totalDays }} 天跨度</span>
        </div>
      </div>

      <button
        v-if="timeline.nearestEvent"
        class="ml-2 hidden items-center gap-1.5 rounded-full border border-gold/25 bg-gold/[0.07] px-2.5 py-1 text-[10px] text-gold transition hover:bg-gold/15 md:inline-flex"
        @click="timeline.jumpToEvent(timeline.nearestEvent)"
      >
        <span class="h-1 w-1 rotate-45 bg-gold" />
        {{ timeline.nearestEvent.label }}
      </button>

      <div class="ml-auto flex items-center gap-2">
        <span
          v-if="timeline.isBeyondCoverage"
          class="hidden items-center gap-1 rounded-full border border-vermilion/30 bg-vermilion/10 px-2 py-1 text-[10px] text-vermilion-bright sm:inline-flex"
        >
          <AppIcon name="info" :size="11" />
          超出收录范围 · 显示最后已知状态
        </span>
        <button class="btn-ghost h-7 px-2 text-[10px]" title="切换播放速度" @click="cycleSpeed">
          {{ timeline.playbackSpeed }}×
        </button>
        <button class="btn-ghost h-7 px-2 text-[10px]" @click="timeline.goToToday()">
          今天
        </button>
      </div>
    </div>

    <!-- ruler -->
    <div class="px-5 pb-3">
      <div
        ref="track"
        class="relative h-[46px] cursor-ew-resize touch-none"
        role="slider"
        tabindex="0"
        aria-label="历史时间轴"
        :aria-valuemin="20121108"
        :aria-valuemax="Number(dayjs(timeline.rangeEnd).format('YYYYMMDD'))"
        :aria-valuenow="Number(dayjs(timeline.currentDate).format('YYYYMMDD'))"
        :aria-valuetext="timeline.currentDate"
        @pointerdown="onPointerDown"
        @pointermove="onPointerMove"
        @pointerup="onPointerUp"
        @pointercancel="onPointerUp"
        @pointerleave="onPointerLeave"
      >
        <!-- baseline -->
        <div class="absolute inset-x-0 top-[18px] h-px bg-white/10" />
        <div
          class="absolute left-0 top-[18px] h-px bg-gradient-to-r from-vermilion-deep via-vermilion to-vermilion-bright"
          :style="{ width: `${timeline.progress * 100}%` }"
        />

        <!-- year ticks -->
        <div
          v-for="tick in yearTicks"
          :key="tick.year"
          class="pointer-events-none absolute top-[13px]"
          :style="{ left: `${tick.ratio * 100}%` }"
        >
          <span class="block h-[9px] w-px bg-white/20" />
          <span
            class="absolute left-0 top-[14px] -translate-x-1/2 text-[9px] tabular-nums tracking-widest text-paper-faint/80"
          >
            {{ tick.year }}
          </span>
        </div>

        <!-- event markers -->
        <button
          v-for="event in timeline.eventMarkers"
          :key="event.date"
          class="group absolute top-[12px] z-10 -translate-x-1/2 p-2"
          :style="{ left: `${event.ratio * 100}%` }"
          :aria-label="`${event.label} ${event.date}`"
          @pointerdown.stop
          @click.stop="timeline.jumpToEvent(event)"
        >
          <span
            class="block h-2 w-2 rotate-45 border border-gold/70 bg-ink-900 transition group-hover:border-gold group-hover:bg-gold"
          />
          <span
            class="pointer-events-none absolute bottom-full left-1/2 mb-1 hidden -translate-x-1/2 whitespace-nowrap rounded border border-white/10 bg-ink-800/95 px-2 py-1 text-[10px] text-paper-dim shadow-panel group-hover:block"
          >
            {{ event.label }} · {{ formatDate(event.date, "YYYY.MM") }}
          </span>
        </button>

        <!-- hover ghost -->
        <div
          v-if="hoverRatio !== null && !dragging"
          class="pointer-events-none absolute top-[10px] h-4 w-px bg-white/25"
          :style="{ left: `${hoverRatio * 100}%` }"
        >
          <span
            class="absolute bottom-full left-1/2 mb-1 -translate-x-1/2 whitespace-nowrap rounded bg-ink-800/95 px-1.5 py-0.5 text-[9px] tabular-nums text-paper-dim"
          >
            {{ hoverDate }}
          </span>
        </div>

        <!-- thumb -->
        <div
          class="pointer-events-none absolute bottom-0 top-[4px] z-20 w-px bg-vermilion"
          :class="timeline.isScrubbing ? '' : 'transition-[left] duration-200 ease-out'"
          :style="{ left: `${timeline.progress * 100}%` }"
        >
          <span class="absolute -left-[6px] top-[10px] block h-3 w-3 rotate-45 border border-white/70 bg-vermilion shadow-[0_0_18px_rgba(200,73,47,.8)]" />
          <span
            v-if="timeline.isScrubbing"
            class="absolute bottom-full left-1/2 mb-2 -translate-x-1/2 whitespace-nowrap rounded border border-vermilion/40 bg-ink-900/95 px-2 py-0.5 text-[10px] tabular-nums text-paper shadow-panel"
          >
            {{ formatDate(timeline.currentDate, "YYYY.MM.DD") }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>
