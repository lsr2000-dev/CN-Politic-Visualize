import { computed, ref } from "vue";
import { defineStore } from "pinia";
import { useStorage } from "@vueuse/core";
import type { ViewMode } from "@/types";

export const useEntityPanelStore = defineStore("entity-panel", () => {
  const activeCentralId = ref<string | null>(null);
  const mode = useStorage<ViewMode>("polvis:entity-panel-mode", "sidebar");
  const pinned = useStorage<string[]>("polvis:entity-pins", []);

  const activeKey = computed(() =>
    activeCentralId.value ? `central:${activeCentralId.value}` : null,
  );

  const isPinned = computed(() =>
    activeKey.value ? pinned.value.includes(activeKey.value) : false,
  );

  function openCentral(id: string): void {
    activeCentralId.value = id;
  }

  function close(): void {
    activeCentralId.value = null;
  }

  function setMode(next: ViewMode): void {
    mode.value = next;
  }

  function togglePin(): boolean {
    if (!activeKey.value) return false;
    if (pinned.value.includes(activeKey.value)) {
      pinned.value = pinned.value.filter((item) => item !== activeKey.value);
      return false;
    }
    pinned.value = [...pinned.value, activeKey.value].slice(-6);
    return true;
  }

  function removePin(key: string): void {
    pinned.value = pinned.value.filter((item) => item !== key);
  }

  return {
    activeCentralId,
    activeKey,
    mode,
    pinned,
    isPinned,
    openCentral,
    close,
    setMode,
    togglePin,
    removePin,
  };
});
