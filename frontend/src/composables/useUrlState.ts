import { watch } from "vue";
import { useDebounceFn } from "@vueuse/core";
import { useAppStore } from "@/stores/app";
import { useMapStore } from "@/stores/map";
import { useTimelineStore } from "@/stores/timeline";

/**
 * Keeps the current date / region / view in the URL so any slice can be
 * bookmarked and shared: /?date=2017-10-25&region=310000&view=fullscreen
 */
export function useUrlState() {
  const app = useAppStore();
  const timeline = useTimelineStore();
  const map = useMapStore();

  const sync = useDebounceFn(
    () => {
      if (!app.ready) return;
      const params = new URLSearchParams();
      params.set("date", timeline.currentDate);
      if (map.selectedRegionCode) params.set("region", map.selectedRegionCode);
      params.set("view", map.viewMode);
      if (app.directoryOpen) params.set("directory", "1");
      const url = `${window.location.pathname}?${params.toString()}`;
      window.history.replaceState(window.history.state, "", url);
    },
    320,
    { maxWait: 1200 },
  );

  watch(
    [() => timeline.currentDate, () => map.selectedRegionCode, () => map.viewMode,
     () => app.directoryOpen],
    () => sync(),
  );
}
