import { watch } from "vue";
import { useDebounceFn } from "@vueuse/core";
import { useAppStore } from "@/stores/app";
import { useMapStore } from "@/stores/map";
import { useTimelineStore } from "@/stores/timeline";

/**
 * Bridges the timeline with the snapshot endpoint.
 *
 * During a drag `currentDate` changes on every pointermove. The fetch is
 * debounced (180ms trailing, 420ms maxWait) so continuous scrubbing still
 * refreshes the map roughly every 400ms without flooding the API.
 */
export function useSnapshotSync() {
  const timeline = useTimelineStore();
  const map = useMapStore();
  const app = useAppStore();

  const fetchSnapshot = useDebounceFn(
    (date: string) => {
      if (!app.ready) return;
      void map.loadSnapshot(date);
    },
    180,
    { maxWait: 420 },
  );

  watch(
    () => timeline.currentDate,
    (date) => fetchSnapshot(date),
  );

  function refresh(): void {
    void map.loadSnapshot(timeline.currentDate, true);
  }

  return { refresh };
}
