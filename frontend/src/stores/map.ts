import { computed, ref, shallowRef } from "vue";
import { defineStore } from "pinia";
import { useStorage } from "@vueuse/core";
import axios from "axios";
import { getSnapshot } from "@/api/client";
import type {
  MetaResponse,
  MetricKey,
  RegionSnapshot,
  SnapshotResponse,
  ViewMode,
} from "@/types";

export const useMapStore = defineStore("map", () => {
  const snapshot = ref<SnapshotResponse | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const selectedRegionCode = ref<string | null>(null);
  const hoveredRegionCode = ref<string | null>(null);
  const viewMode = useStorage<ViewMode>("polvis:view-mode", "sidebar");
  const metric = useStorage<MetricKey>("polvis:metric", "party_days");
  const pinnedRegions = useStorage<string[]>("polvis:pins", ["110000", "310000", "440000"]);
  const compareOpen = ref(false);
  const loadedDate = ref<string | null>(null);
  const lastLoadedAt = ref<number | null>(null);

  let controller: AbortController | null = null;
  let requestSeq = 0;

  const regions = computed<RegionSnapshot[]>(() => snapshot.value?.regions ?? []);
  const selectedRegion = computed<RegionSnapshot | null>(
    () => regions.value.find((region) => region.region_code === selectedRegionCode.value) ?? null,
  );
  const hoveredRegion = computed<RegionSnapshot | null>(
    () => regions.value.find((region) => region.region_code === hoveredRegionCode.value) ?? null,
  );
  const pinnedRegionObjects = computed<RegionSnapshot[]>(() =>
    pinnedRegions.value
      .map((code) => regions.value.find((region) => region.region_code === code))
      .filter((region): region is RegionSnapshot => Boolean(region)),
  );
  const hasSelection = computed(() => Boolean(selectedRegionCode.value));
  const isPinned = (code: string | null): boolean =>
    Boolean(code && pinnedRegions.value.includes(code));

  async function loadSnapshot(date: string, force = false): Promise<void> {
    controller?.abort();
    const current = new AbortController();
    controller = current;
    const seq = ++requestSeq;
    loading.value = true;
    error.value = null;
    try {
      const data = await getSnapshot(date, { signal: current.signal, force });
      if (seq !== requestSeq) return;
      snapshot.value = data;
      loadedDate.value = data.as_of;
      lastLoadedAt.value = Date.now();
      if (!selectedRegionCode.value && data.regions.length > 0) {
        // Keep an empty map first; user selects explicitly. This preserves the
        // "点击省份下探" interaction instead of auto-opening a panel.
      }
    } catch (caught) {
      if (axios.isCancel(caught)) return;
      if (seq !== requestSeq) return;
      error.value = caught instanceof Error ? caught.message : "快照加载失败";
    } finally {
      if (seq === requestSeq) loading.value = false;
    }
  }

  function selectRegion(code: string | null): void {
    selectedRegionCode.value = code;
  }

  function setViewMode(mode: ViewMode): void {
    viewMode.value = mode;
    if (mode === "fullscreen" && !selectedRegionCode.value) {
      selectedRegionCode.value = "110000";
    }
  }

  function togglePin(code: string): boolean {
    const index = pinnedRegions.value.indexOf(code);
    if (index >= 0) {
      pinnedRegions.value = pinnedRegions.value.filter((item) => item !== code);
      return false;
    }
    if (pinnedRegions.value.length >= 6) {
      pinnedRegions.value = [...pinnedRegions.value.slice(1), code];
      return true;
    }
    pinnedRegions.value = [...pinnedRegions.value, code];
    return true;
  }

  function removePin(code: string): void {
    pinnedRegions.value = pinnedRegions.value.filter((item) => item !== code);
  }

  function openCompare(): void {
    if (pinnedRegions.value.length >= 2) compareOpen.value = true;
  }

  function resetPins(): void {
    pinnedRegions.value = [];
  }

  function setMetric(value: MetricKey): void {
    metric.value = value;
  }

  function regionByCode(code: string | null): RegionSnapshot | null {
    if (!code) return null;
    return regions.value.find((region) => region.region_code === code) ?? null;
  }

  return {
    snapshot,
    regions,
    loading,
    error,
    selectedRegionCode,
    selectedRegion,
    hoveredRegionCode,
    hoveredRegion,
    viewMode,
    metric,
    pinnedRegions,
    pinnedRegionObjects,
    compareOpen,
    loadedDate,
    lastLoadedAt,
    hasSelection,
    isPinned,
    loadSnapshot,
    selectRegion,
    setViewMode,
    togglePin,
    removePin,
    openCompare,
    resetPins,
    setMetric,
    regionByCode,
  };
});
