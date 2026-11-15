import { computed, onScopeDispose, ref } from "vue";
import { defineStore } from "pinia";
import dayjs from "dayjs";
import { clamp } from "@/utils/format";
import type { EventInfo, MetaResponse } from "@/types";

export const useTimelineStore = defineStore("timeline", () => {
  const rangeStart = ref("2012-11-08");
  const rangeEnd = ref(dayjs().format("YYYY-MM-DD"));
  const coverageEnd = ref("2025-06-30");
  const currentDate = ref("2025-06-30");
  const isScrubbing = ref(false);
  const isPlaying = ref(false);
  const playbackSpeed = ref(1);
  const events = ref<EventInfo[]>([]);
  const initialized = ref(false);

  let raf = 0;
  let timer: number | undefined;

  const totalDays = computed(() =>
    Math.max(1, dayjs(rangeEnd.value).diff(dayjs(rangeStart.value), "day")),
  );

  const progress = computed(() =>
    clamp(dayjs(currentDate.value).diff(dayjs(rangeStart.value), "day") / totalDays.value, 0, 1),
  );

  const isBeyondCoverage = computed(() =>
    dayjs(currentDate.value).isAfter(dayjs(coverageEnd.value), "day"),
  );

  const nearestEvent = computed(() => {
    const target = dayjs(currentDate.value);
    let best: EventInfo | null = null;
    let distance = Number.POSITIVE_INFINITY;
    for (const event of events.value) {
      const diff = Math.abs(dayjs(event.date).diff(target, "day"));
      if (diff < distance) {
        distance = diff;
        best = event;
      }
    }
    return distance <= 45 ? best : null;
  });

  const eventMarkers = computed(() =>
    events.value
      .filter((event) => {
        const day = dayjs(event.date);
        return day.isAfter(dayjs(rangeStart.value)) && day.isBefore(dayjs(rangeEnd.value));
      })
      .map((event) => ({
        ...event,
        ratio: dayjs(event.date).diff(dayjs(rangeStart.value), "day") / totalDays.value,
      })),
  );

  function clampDate(value: string): string {
    const day = dayjs(value);
    if (day.isBefore(dayjs(rangeStart.value))) return rangeStart.value;
    if (day.isAfter(dayjs(rangeEnd.value))) return rangeEnd.value;
    return day.format("YYYY-MM-DD");
  }

  function setDate(value: string): void {
    currentDate.value = clampDate(value);
  }

  function setScrubbing(value: boolean): void {
    isScrubbing.value = value;
    if (value) pause();
  }

  function step(days: number): void {
    setDate(dayjs(currentDate.value).add(days, "day").format("YYYY-MM-DD"));
  }

  function stepMonth(months: number): void {
    setDate(dayjs(currentDate.value).add(months, "month").format("YYYY-MM-DD"));
  }

  function animateTo(target: string, duration = 480): void {
    if (raf) cancelAnimationFrame(raf);
    const from = dayjs(currentDate.value).startOf("day").valueOf();
    const to = dayjs(clampDate(target)).startOf("day").valueOf();
    if (Math.abs(to - from) < 2) {
      setDate(target);
      return;
    }
    const startedAt = performance.now();
    const tick = (now: number) => {
      const t = clamp((now - startedAt) / duration, 0, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      const value = Math.round(from + (to - from) * eased);
      currentDate.value = dayjs(value).format("YYYY-MM-DD");
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
  }

  function jumpToEvent(event: EventInfo): void {
    animateTo(event.date, 620);
  }

  function pause(): void {
    isPlaying.value = false;
    if (timer) {
      window.clearInterval(timer);
      timer = undefined;
    }
  }

  function play(): void {
    if (isPlaying.value) return;
    if (dayjs(currentDate.value).isAfter(dayjs(rangeEnd.value).subtract(1, "month"))) {
      currentDate.value = rangeStart.value;
    }
    isPlaying.value = true;
    const tick = () => {
      const next = dayjs(currentDate.value).add(1, "month");
      if (next.isAfter(dayjs(rangeEnd.value))) {
        setDate(rangeEnd.value);
        pause();
        return;
      }
      setDate(next.format("YYYY-MM-DD"));
    };
    tick();
    timer = window.setInterval(tick, Math.max(240, 900 / playbackSpeed.value));
  }

  function togglePlay(): void {
    if (isPlaying.value) pause();
    else play();
  }

  function setPlaybackSpeed(speed: number): void {
    playbackSpeed.value = speed;
    if (isPlaying.value) {
      pause();
      play();
    }
  }

  function initialize(meta: MetaResponse): void {
    rangeStart.value = meta.dataset.coverage_start;
    coverageEnd.value = meta.dataset.coverage_end;
    rangeEnd.value = dayjs().format("YYYY-MM-DD");
    events.value = meta.events;
    if (!initialized.value) {
      const preferred = dayjs(meta.dataset.coverage_end).isAfter(dayjs(rangeEnd.value))
        ? rangeEnd.value
        : meta.dataset.coverage_end;
      currentDate.value = preferred;
      initialized.value = true;
    }
  }

  function goToToday(): void {
    animateTo(rangeEnd.value, 700);
  }

  onScopeDispose(() => {
    pause();
    if (raf) cancelAnimationFrame(raf);
  });

  return {
    currentDate,
    rangeStart,
    rangeEnd,
    coverageEnd,
    isScrubbing,
    isPlaying,
    playbackSpeed,
    events,
    initialized,
    totalDays,
    progress,
    isBeyondCoverage,
    nearestEvent,
    eventMarkers,
    setDate,
    setScrubbing,
    step,
    stepMonth,
    animateTo,
    jumpToEvent,
    play,
    pause,
    togglePlay,
    setPlaybackSpeed,
    initialize,
    goToToday,
  };
});
