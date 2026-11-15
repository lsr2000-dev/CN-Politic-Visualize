<script setup lang="ts">
import { computed, onScopeDispose, ref } from "vue";
import { onClickOutside } from "@vueuse/core";
import AppIcon from "./ui/AppIcon.vue";
import { useMapStore } from "@/stores/map";
import { useAppStore } from "@/stores/app";
import { metricDomain, metricGradient, metricLegendLabels, metricValue } from "@/utils/mapColor";
import type { MetricKey } from "@/types";

const map = useMapStore();
const app = useAppStore();
const open = ref(false);
const root = ref<HTMLElement | null>(null);

onClickOutside(root, () => {
  open.value = false;
});

const options = computed<Array<{ key: MetricKey; label: string; unit: string }>>(
  () =>
    app.meta?.metrics.map((metric) => ({
      key: metric.key,
      label: metric.label,
      unit: metric.unit,
    })) ?? [],
);

const current = computed(
  () => options.value.find((option) => option.key === map.metric) ?? options.value[0],
);

const domain = computed(() => metricDomain(map.regions, map.metric));
const labels = computed(() => metricLegendLabels(map.metric, domain.value));
const gradient = computed(() => metricGradient(map.metric));
const average = computed(() => {
  if (!map.regions.length) return 0;
  const total = map.regions.reduce((sum, region) => sum + metricValue(region, map.metric), 0);
  return Math.round(total / map.regions.length);
});
</script>

<template>
  <div
    ref="root"
    class="pointer-events-auto relative w-[210px] rounded-xl glass hairline p-2.5 shadow-panel sm:w-[228px] sm:p-3"
  >
    <div class="flex items-center justify-between">
      <span class="label-eyebrow">着色指标 / METRIC</span>
      <button
        class="text-paper-faint transition hover:text-paper"
        :aria-expanded="open"
        aria-label="切换着色指标"
        @click="open = !open"
      >
        <AppIcon
          name="chevron-down"
          :size="13"
          :class="['transition-transform duration-300', open ? 'rotate-180' : '']"
        />
      </button>
    </div>

    <button class="mt-1 flex w-full items-baseline justify-between gap-2 text-left" @click="open = !open">
      <span class="text-[13px] leading-tight text-paper">{{ current?.label }}</span>
      <span class="shrink-0 text-[10px] text-paper-faint">{{ current?.unit }}</span>
    </button>

    <Transition name="scale">
      <div
        v-if="open"
        class="absolute bottom-full left-0 z-20 mb-2 w-full overflow-hidden rounded-lg border border-white/10 bg-ink-900/95 p-1 shadow-panel backdrop-blur-xl"
      >
        <button
          v-for="option in options"
          :key="option.key"
          class="flex w-full items-center justify-between rounded-md px-2 py-1.5 text-left text-[11px] transition"
          :class="option.key === map.metric
            ? 'bg-vermilion/15 text-paper'
            : 'text-paper-dim hover:bg-white/[0.06] hover:text-paper'"
          @click="map.setMetric(option.key); open = false"
        >
          <span>{{ option.label }}</span>
          <AppIcon v-if="option.key === map.metric" name="check" :size="12" class="text-vermilion-bright" />
        </button>
      </div>
    </Transition>

    <div class="mt-3">
      <div class="h-1.5 w-full rounded-full" :style="{ background: gradient }" />
      <div class="mt-1.5 flex items-center justify-between text-[10px] tabular-nums text-paper-faint">
        <span>{{ labels[0] }}</span>
        <span class="text-paper-dim">均值 {{ average }}{{ current?.unit === "天" ? "天" : "" }}</span>
        <span>{{ labels[1] }}</span>
      </div>
      <div class="mt-1 text-[8px] tracking-wide text-paper-faint/60">
        {{ map.metric === "filled" ? "按已收录班子类别数着色" : "按 31 省分位着色 · 0 天表示现任起始待考" }}
      </div>
    </div>

    <div class="mt-3 flex items-center justify-between border-t border-white/[0.06] pt-2 text-[10px] text-paper-faint">
      <span><span class="text-paper-dim">{{ map.regions.length }}</span> 省级行政区</span>
      <span class="inline-flex items-center gap-1">
        <span class="h-1 w-1 rounded-full bg-vermilion live-dot" />
        {{ map.snapshot?.stats.acting_count ?? 0 }} 代理在任
      </span>
    </div>
  </div>
</template>
