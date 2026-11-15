<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from "vue";
import * as echarts from "echarts/core";
import { MapChart } from "echarts/charts";
import { TooltipComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import { useMapStore } from "@/stores/map";
import { formatDuration } from "@/utils/format";
import { metricColor, metricDomain, metricRankMap, metricValue } from "@/utils/mapColor";
import type { GeoJson, Member, RegionSnapshot } from "@/types";

echarts.use([MapChart, TooltipComponent, CanvasRenderer]);

const props = defineProps<{ geo: GeoJson }>();
const map = useMapStore();

const container = ref<HTMLDivElement | null>(null);
const chart = shallowRef<ReturnType<typeof echarts.init> | null>(null);

const regions = computed(() => map.regions);
const byName = computed(() => {
  const dict = new Map<string, RegionSnapshot>();
  for (const region of regions.value) dict.set(region.region_name, region);
  return dict;
});
const byCode = computed(() => {
  const dict = new Map<string, RegionSnapshot>();
  for (const region of regions.value) dict.set(region.region_code, region);
  return dict;
});

function shortName(name: string): string {
  const region = byName.value.get(name);
  if (region) return region.short_name;
  return name.replace(/(维吾尔|壮族|回族)?(自治区|特别行政区|省|市)$/g, "") || name;
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (char) => {
    switch (char) {
      case "&":
        return "&amp;";
      case "<":
        return "&lt;";
      case ">":
        return "&gt;";
      case '"':
        return "&quot;";
      default:
        return "&#39;";
    }
  });
}

function memberRow(label: string, color: string, member: Member | null): string {
  if (!member) {
    return `<div style="display:flex;align-items:center;gap:8px;padding:3px 0;color:#6e7681;font-size:11px">
      <span style="width:5px;height:5px;border-radius:50%;background:${color};opacity:.45"></span>
      <span style="width:28px">${label}</span><span>未收录</span></div>`;
  }
  const acting = member.is_acting
    ? '<span style="margin-left:4px;padding:0 4px;border:1px solid rgba(200,73,47,.55);border-radius:3px;color:#e07a5f;font-size:9px">代</span>'
    : "";
  return `<div style="display:flex;align-items:center;gap:8px;padding:3px 0;font-size:11px">
    <span style="width:5px;height:5px;border-radius:50%;background:${color}"></span>
    <span style="width:28px;color:#8b93a1">${label}</span>
    <span style="color:#f1ece1;font-weight:600">${escapeHtml(member.officer.name)}</span>${acting}
    <span style="margin-left:auto;color:#7d8593;font-size:10px">${formatDuration(member.duration_days)}</span>
  </div>`;
}

function tooltipHtml(region: RegionSnapshot): string {
  const head = `<div style="display:flex;align-items:baseline;gap:8px;margin-bottom:6px">
    <span style="font-family:'Noto Serif SC',serif;font-size:15px;color:#f5f0e4">${escapeHtml(region.region_name)}</span>
    <span style="font-size:9px;letter-spacing:.12em;color:#6e7681">${region.region_code}</span>
    <span style="margin-left:auto;font-size:10px;color:${region.filled === 4 ? "#8fbfa5" : "#b08a4a"}">${region.filled}/4 收录</span>
  </div>`;
  return `<div style="min-width:238px">${head}
    ${memberRow("党委", "#c8492f", region.teams.party.members[0] ?? null)}
    ${memberRow("政府", "#b08a4a", region.teams.government.members[0] ?? null)}
    ${memberRow("人大", "#4d7ea8", region.teams.congress.members[0] ?? null)}
    ${memberRow("政协", "#5c8a76", region.teams.cppcc.members[0] ?? null)}
    <div style="margin-top:6px;padding-top:6px;border-top:1px solid rgba(255,255,255,.08);display:flex;justify-content:space-between;font-size:9px;color:#6e7681">
      <span>点击省份下探</span><span>${region.metrics.party_count} 任书记 / ${region.metrics.governor_count} 任省长</span>
    </div></div>`;
}

function buildData() {
  const domain = metricDomain(regions.value, map.metric);
  const ranks = metricRankMap(regions.value, map.metric);
  return regions.value.map((region) => {
    const value = metricValue(region, map.metric);
    return {
      name: region.region_name,
      value,
      code: region.region_code,
      itemStyle: {
        areaColor: metricColor(value, map.metric, domain, ranks.get(region.region_code)),
      },
    };
  });
}

function buildMarkPoint() {
  const region = map.selectedRegionCode ? byCode.value.get(map.selectedRegionCode) : undefined;
  if (!region?.centroid) return { data: [] };
  return {
    silent: true,
    symbol: "circle",
    symbolSize: 22,
    itemStyle: {
      color: "rgba(200,73,47,0.12)",
      borderColor: "rgba(255,194,174,0.85)",
      borderWidth: 1,
    },
    label: { show: false },
    data: [{ coord: region.centroid, name: region.short_name }],
  };
}

function buildOption(): echarts.EChartsCoreOption {
  const narrow = (container.value?.clientWidth ?? 1000) < 640;
  return {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "item",
      confine: true,
      backgroundColor: "rgba(9,12,17,.97)",
      borderColor: "rgba(255,255,255,.12)",
      borderWidth: 1,
      padding: [10, 12],
      textStyle: { color: "#e8e0cd", fontSize: 12 },
      extraCssText: "border-radius:10px;box-shadow:0 18px 50px -12px rgba(0,0,0,.9);",
      formatter: (params: { name?: string }) => {
        const region = params.name ? byName.value.get(params.name) : undefined;
        if (!region) {
          return `<div style="font-size:11px;color:#8b93a1;padding:2px 4px">${escapeHtml(params.name ?? "")}<br/><span style="font-size:10px;color:#5f6875">未纳入本次统计（31 个省级行政区）</span></div>`;
        }
        return tooltipHtml(region);
      },
    },
    series: [
      {
        type: "map",
        map: "china",
        roam: true,
        selectedMode: "single",
        zoom: narrow ? 1.06 : 1.42,
        center: narrow ? [104.4, 36.0] : [104.2, 35.8],
        scaleLimit: { min: 0.85, max: 6 },
        label: {
          show: true,
          color: "rgba(232,224,205,.6)",
          fontSize: narrow ? 8 : 9,
          fontFamily: "'PingFang SC','Microsoft YaHei',sans-serif",
          formatter: (params: { name?: string }) => shortName(params.name ?? ""),
        },
        itemStyle: {
          areaColor: "#151d26",
          borderColor: "rgba(176,138,74,.38)",
          borderWidth: 0.7,
        },
        emphasis: {
          label: { show: true, color: "#fff", fontSize: 11, fontWeight: 600 },
          itemStyle: {
            areaColor: "#2c3c49",
            borderColor: "#e07050",
            borderWidth: 1.2,
            shadowBlur: 20,
            shadowColor: "rgba(200,73,47,.35)",
          },
        },
        select: {
          label: { show: true, color: "#fff", fontSize: 11, fontWeight: 600 },
          itemStyle: {
            areaColor: "#b9432c",
            borderColor: "#ffc2ae",
            borderWidth: 1.4,
            shadowBlur: 28,
            shadowColor: "rgba(200,73,47,.6)",
          },
        },
        data: buildData(),
        markPoint: buildMarkPoint(),
        animationDuration: 720,
        animationDurationUpdate: 420,
        animationEasingUpdate: "cubicOut",
      },
    ],
  };
}

function initChart(): void {
  if (!container.value) return;
  chart.value = echarts.init(container.value, undefined, { renderer: "canvas" });
  echarts.registerMap("china", props.geo as never);
  chart.value.setOption(buildOption());

  chart.value.on("click", (params: { name?: string }) => {
    const region = params.name ? byName.value.get(params.name) : undefined;
    if (region) map.selectRegion(region.region_code);
  });
  chart.value.on("mouseover", (params: { name?: string }) => {
    const region = params.name ? byName.value.get(params.name) : undefined;
    map.hoveredRegionCode = region?.region_code ?? null;
  });
  chart.value.on("globalout", () => {
    map.hoveredRegionCode = null;
  });

  applySelection(map.selectedRegionCode);
}

function updateData(): void {
  if (!chart.value) return;
  chart.value.setOption({
    series: [{ data: buildData(), markPoint: buildMarkPoint() }],
  });
  applySelection(map.selectedRegionCode);
}

function applySelection(code: string | null): void {
  if (!chart.value) return;
  chart.value.setOption({ series: [{ markPoint: buildMarkPoint() }] });
  const name = code ? byCode.value.get(code)?.region_name : undefined;
  if (name) {
    chart.value.dispatchAction({ type: "select", name });
  } else {
    chart.value.dispatchAction({ type: "unselect", seriesIndex: 0 });
  }
}

let resizeObserver: ResizeObserver | null = null;
let resizeTimer = 0;

onMounted(async () => {
  await nextTick();
  initChart();
  if (container.value) {
    resizeObserver = new ResizeObserver(() => {
      window.clearTimeout(resizeTimer);
      resizeTimer = window.setTimeout(() => chart.value?.resize(), 80);
    });
    resizeObserver.observe(container.value);
  }
});

onBeforeUnmount(() => {
  resizeObserver?.disconnect();
  window.clearTimeout(resizeTimer);
  chart.value?.dispose();
  chart.value = null;
});

watch(
  () => props.geo,
  () => {
    if (chart.value) {
      echarts.registerMap("china", props.geo as never);
      chart.value.setOption(buildOption());
      applySelection(map.selectedRegionCode);
    }
  },
);

watch([regions, () => map.metric], updateData);
watch(
  () => map.selectedRegionCode,
  (code) => applySelection(code),
);
</script>

<template>
  <div ref="container" class="h-full w-full" role="img" aria-label="中国省级行政区人事快照地图" />
</template>
