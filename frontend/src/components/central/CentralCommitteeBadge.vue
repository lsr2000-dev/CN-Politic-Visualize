<script setup lang="ts">
import { computed } from "vue";
import type { CentralCommittee } from "@/types";

const props = defineProps<{ committee: CentralCommittee | null; compact?: boolean }>();

const tone = computed(() => {
  if (!props.committee) return "";
  if (props.committee.status === "expelled") return "border-vermilion/70 text-vermilion-bright bg-vermilion/10";
  if (props.committee.status === "active") return "border-gold/45 text-gold bg-gold/[0.08]";
  return "border-white/15 text-paper-faint bg-white/[0.03]";
});
</script>

<template>
  <span
    v-if="committee"
    class="inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[9px] leading-none"
    :class="[tone, compact ? 'px-1' : '']"
    :title="committee.status_note || committee.label"
  >
    <span>{{ committee.label }}</span>
    <span v-if="committee.status !== 'active'" class="opacity-80">· {{ committee.status_label }}</span>
  </span>
</template>
