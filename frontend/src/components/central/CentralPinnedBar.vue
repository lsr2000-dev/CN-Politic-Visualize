<script setup lang="ts">
import { computed } from "vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import { useCentralStore } from "@/stores/central";
import { useEntityPanelStore } from "@/stores/entityPanel";
import { useTimelineStore } from "@/stores/timeline";
import type { CentralInstitution } from "@/types";

const central = useCentralStore();
const panel = useEntityPanelStore();
const timeline = useTimelineStore();

const items = computed<Array<{ key: string; institution: CentralInstitution }>>(() => {
  const result: Array<{ key: string; institution: CentralInstitution }> = [];
  for (const key of panel.pinned) {
    if (!key.startsWith("central:")) continue;
    const id = key.slice("central:".length);
    const institution = (central.org?.institutions ?? []).find((i) => i.id === id);
    if (institution) result.push({ key, institution });
  }
  return result;
});

function open(id: string): void {
  const institution = (central.org?.institutions ?? []).find((i) => i.id === id);
  if (institution) void central.selectInstitution(institution, timeline.currentDate);
}
</script>

<template>
  <div v-if="items.length" class="central-pin-bar">
    <span class="flex items-center gap-1 text-[8px] tracking-[0.18em] text-paper-faint/70">
      <AppIcon name="pin" :size="10" /> PINNED
    </span>
    <button
      v-for="item in items"
      :key="item.key"
      class="inline-flex items-center gap-1 rounded-full border border-gold/25 bg-gold/[0.06] px-2 py-0.5 text-[9px] text-gold transition hover:border-gold/50"
      @click="open(item.institution.id)"
    >
      {{ item.institution.short_name || item.institution.name }}
      <span
        class="ml-0.5 flex h-3 w-3 items-center justify-center rounded-full text-paper-faint/70 hover:bg-white/10 hover:text-vermilion-bright"
        @click.stop="panel.removePin(item.key)"
      >
        <AppIcon name="close" :size="8" />
      </span>
    </button>
  </div>
</template>

<style scoped>
.central-pin-bar {
  position: fixed;
  left: 20px;
  bottom: 84px;
  z-index: 58;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  max-width: min(520px, calc(100vw - 40px));
  padding: 5px 8px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 999px;
  background: rgba(9, 12, 17, 0.88);
  backdrop-filter: blur(14px);
}
@media (max-width: 768px) {
  .central-pin-bar { bottom: 74px; left: 12px; }
}
</style>
