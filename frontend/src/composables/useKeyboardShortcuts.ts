import { onMounted, onScopeDispose } from "vue";
import { useAppStore, useOfficerStore } from "@/stores/app";
import { useMapStore } from "@/stores/map";
import { useTimelineStore } from "@/stores/timeline";

export function useKeyboardShortcuts() {
  const timeline = useTimelineStore();
  const map = useMapStore();
  const app = useAppStore();
  const officer = useOfficerStore();

  function handler(event: KeyboardEvent): void {
    const target = event.target as HTMLElement | null;
    if (
      target &&
      (["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName) || target.isContentEditable)
    ) {
      return;
    }

    switch (event.key) {
      case "Escape":
        if (app.searchOpen) app.closeSearch();
        else if (officer.overlay) officer.closeAll();
        else if (map.compareOpen) map.compareOpen = false;
        else if (app.directoryOpen) app.closeDirectory();
        else if (map.selectedRegionCode) map.selectRegion(null);
        break;
      case "/":
        event.preventDefault();
        app.openSearch();
        break;
      case " ":
        event.preventDefault();
        timeline.togglePlay();
        break;
      case "ArrowLeft":
        event.preventDefault();
        if (event.shiftKey) timeline.stepMonth(-1);
        else timeline.step(-1);
        break;
      case "ArrowRight":
        event.preventDefault();
        if (event.shiftKey) timeline.stepMonth(1);
        else timeline.step(1);
        break;
      case "Home":
        event.preventDefault();
        timeline.setDate(timeline.rangeStart);
        break;
      case "End":
        event.preventDefault();
        timeline.setDate(timeline.rangeEnd);
        break;
      default:
        break;
    }
  }

  onMounted(() => window.addEventListener("keydown", handler));
  onScopeDispose(() => window.removeEventListener("keydown", handler));
}
