<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useDebounceFn } from "@vueuse/core";
import AppIcon from "./ui/AppIcon.vue";
import { useMapStore } from "@/stores/map";
import { useTimelineStore } from "@/stores/timeline";
import { getCompare } from "@/api/client";
import { categoryColor, formatDate, formatDuration } from "@/utils/format";
import type { CompareResponse, Member } from "@/types";

const map = useMapStore();
const timeline = useTimelineStore();

const data = ref<CompareResponse | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);
let controller: AbortController | null = null;

const regions = computed(() => data.value?.regions ?? []);
const teams = [
  { key: "party", label: "党委" },
  { key: "congress", label: "人大" },
  { key: "government", label: "政府" },
  { key: "cppcc", label: "政协" },
] as const;

const metrics = [
  { key: "party_days", label: "书记在任", format: (value: number) => formatDuration(value) },
  { key: "governor_days", label: "省长在任", format: (value: number) => formatDuration(value) },
  { key: "party_count", label: "书记人数", format: (value: number) => `${value} 人` },
  { key: "filled", label: "班子收录", format: (value: number) => `${value}/4` },
] as const;

const gridStyle = computed(() => ({
  gridTemplateColumns: `118px repeat(${Math.max(regions.value.length, 1)}, minmax(196px, 1fr))`,
}));

async function load(): Promise<void> {
  if (!map.compareOpen || map.pinnedRegions.length < 2) return;
  controller?.abort();
  const current = new AbortController();
  controller = current;
  loading.value = true;
  error.value = null;
  try {
    data.value = await getCompare(map.pinnedRegions, timeline.currentDate, current.signal);
  } catch (caught) {
    if ((caught as Error).name === "CanceledError") return;
    error.value = caught instanceof Error ? caught.message : "对比数据加载失败";
  } finally {
    loading.value = false;
  }
}

const debouncedLoad = useDebounceFn(load, 180);

watch(
  [() => map.compareOpen, () => map.pinnedRegions.join(","), () => timeline.currentDate],
  ([open]) => {
    if (open) void debouncedLoad();
  },
  { immediate: true },
);

watch(
  () => map.pinnedRegions.length,
  (length) => {
    if (length < 2) map.compareOpen = false;
  },
);

function close(): void {
  map.compareOpen = false;
}

function inspect(code: string): void {
  map.selectRegion(code);
  close();
}

function membersOf(regionCode: string, category: string): Member[] {
  const region = regions.value.find((item) => item.region_code === regionCode);
  if (!region) return [];
  return region.teams[category as keyof typeof region.teams]?.members ?? [];
}

function metricValue(regionCode: string, key: string): number {
  const region = regions.value.find((item) => item.region_code === regionCode);
  if (!region) return 0;
  return region.metrics[key as keyof typeof region.metrics] ?? 0;
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="map.compareOpen"
        class="fixed inset-0 z-[70] flex items-center justify-center bg-ink-950/80 p-3 backdrop-blur-md sm:p-6"
        role="dialog"
        aria-label="跨省班子对比"
        @click.self="close"
      >
        <div class="flex max-h-[90vh] w-full max-w-[1400px] flex-col overflow-hidden rounded-xl border border-white/10 bg-ink-950 shadow-panel">
        <header class="flex shrink-0 items-center justify-between border-b border-white/[0.08] bg-ink-900/40 px-5 py-4 sm:px-8">
          <div>
            <div class="flex items-center gap-2">
              <span class="h-3 w-[2px] bg-vermilion" />
              <span class="label-eyebrow">COMPARATIVE VIEW</span>
            </div>
            <h2 class="mt-1 font-display text-[24px] tracking-wide text-paper">跨省班子对比</h2>
            <p class="mt-1 text-[10px] text-paper-faint">
              {{ formatDate(data?.as_of ?? timeline.currentDate, "YYYY 年 MM 月 DD 日") }} ·
              {{ map.pinnedRegions.length }} 省并置 · 同一时点
            </p>
          </div>
          <div class="flex items-center gap-2">
            <button class="btn-ghost hidden sm:inline-flex" @click="map.resetPins(); close()">
              清空钉住
            </button>
            <button class="btn-icon" aria-label="关闭对比" @click="close">
              <AppIcon name="close" :size="16" />
            </button>
          </div>
        </header>

        <div class="min-h-0 flex-1 overflow-auto p-4 sm:p-8">
          <div v-if="error" class="mx-auto max-w-md rounded-xl border border-vermilion/25 bg-ink-900 p-6 text-center">
            <AppIcon name="info" :size="22" class="mx-auto text-vermilion-bright" />
            <p class="mt-3 text-[12px] text-paper">对比数据加载失败</p>
            <p class="mt-1 text-[10px] text-paper-faint">{{ error }}</p>
            <button class="btn-ghost mt-4" @click="load">重试</button>
          </div>

          <div v-else class="mx-auto max-w-[1500px]">
            <div v-if="loading && !data" class="flex flex-col items-center gap-3 py-24">
              <div class="h-1 w-24 overflow-hidden rounded-full bg-white/10">
                <div class="h-full w-1/2 animate-pulse rounded-full bg-vermilion" />
              </div>
              <span class="text-[10px] tracking-[0.2em] text-paper-faint">正在对齐各省时点…</span>
            </div>
            <div
              v-else
              class="grid gap-px overflow-hidden rounded-xl border border-white/[0.08] bg-white/[0.06]"
              :style="gridStyle"
            >
              <!-- corner -->
              <div class="bg-ink-900 px-3 py-3">
                <span class="label-eyebrow">维度 / 省份</span>
              </div>

              <!-- province headers -->
              <div
                v-for="region in regions"
                :key="region.region_code"
                class="group bg-ink-900 px-3 py-3"
              >
                <div class="flex items-start justify-between gap-2">
                  <div class="min-w-0">
                    <div class="truncate font-display text-[20px] leading-tight text-paper">
                      {{ region.short_name }}
                    </div>
                    <div class="mt-1 flex items-center gap-1.5">
                      <span class="text-[9px] tabular-nums tracking-wider text-paper-faint">{{ region.region_code }}</span>
                      <span
                        class="rounded px-1 py-px text-[8px]"
                        :class="region.filled === 4 ? 'bg-jade/15 text-jade' : 'bg-gold/15 text-gold'"
                      >
                        {{ region.filled }}/4
                      </span>
                    </div>
                  </div>
                  <div class="flex shrink-0 items-center gap-0.5 opacity-60 transition group-hover:opacity-100">
                    <button class="btn-icon h-6 w-6" title="查看详情" @click="inspect(region.region_code)">
                      <AppIcon name="arrow-up-right" :size="11" />
                    </button>
                    <button
                      class="btn-icon h-6 w-6"
                      title="移除"
                      @click="map.removePin(region.region_code)"
                    >
                      <AppIcon name="close" :size="11" />
                    </button>
                  </div>
                </div>
              </div>

              <!-- metric rows -->
              <template v-for="metric in metrics" :key="metric.key">
                <div class="flex items-center bg-ink-900/70 px-3 py-2">
                  <span class="text-[10px] text-paper-faint">{{ metric.label }}</span>
                </div>
                <div
                  v-for="region in regions"
                  :key="`${metric.key}-${region.region_code}`"
                  class="bg-ink-900/40 px-3 py-2 text-[12px] tabular-nums text-paper-dim"
                >
                  {{ metric.format(metricValue(region.region_code, metric.key)) }}
                </div>
              </template>

              <!-- team rows -->
              <template v-for="team in teams" :key="team.key">
                <div class="flex items-start gap-2 bg-ink-900/70 px-3 py-3">
                  <span class="mt-1 h-2.5 w-[2px]" :style="{ backgroundColor: categoryColor(team.key) }" />
                  <div>
                    <div class="text-[11px] text-paper">{{ team.label }}</div>
                    <div class="mt-0.5 text-[8px] tracking-[0.18em] text-paper-faint">
                      {{ team.key.toUpperCase() }}
                    </div>
                  </div>
                </div>
                <div
                  v-for="region in regions"
                  :key="`${team.key}-${region.region_code}`"
                  class="min-h-[74px] bg-ink-900/40 px-3 py-2.5"
                >
                  <template v-if="membersOf(region.region_code, team.key).length">
                    <div
                      v-for="member in membersOf(region.region_code, team.key)"
                      :key="member.tenure_id"
                      class="py-1"
                    >
                      <div class="flex items-center gap-1.5">
                        <span class="truncate text-[12px]" :class="member.is_acting ? 'text-paper-dim' : 'text-paper'">
                          {{ member.officer.name }}
                        </span>
                        <span
                          v-if="member.is_acting"
                          class="shrink-0 rounded border border-vermilion/35 px-1 py-px text-[8px] text-vermilion-bright"
                        >
                          代
                        </span>
                        <span class="ml-auto shrink-0 text-[8px] tabular-nums text-paper-faint">
                          {{ formatDuration(member.duration_days) }}
                        </span>
                      </div>
                      <div class="mt-0.5 truncate pl-0 text-[9px] text-paper-faint">
                        {{ member.title }}
                      </div>
                    </div>
                  </template>
                  <span v-else class="text-[10px] text-paper-faint/50">未收录</span>
                </div>
              </template>
            </div>

            <p class="mt-3 flex items-center gap-1.5 px-1 text-[9px] text-paper-faint/70">
              <AppIcon name="info" :size="10" />
              对比基于同一 as_of 时点；代理与兼任记录一并展示，任职时长按数据覆盖截止日计算。
            </p>
            </div>
          </div>

        <footer class="flex shrink-0 items-center justify-between border-t border-white/[0.06] px-5 py-2.5 text-[9px] text-paper-faint sm:px-8">
          <span>钉住省份最多 6 个 · 在详情面板点击图钉加入</span>
          <span class="tabular-nums">POLVIS / COMPARE</span>
        </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
