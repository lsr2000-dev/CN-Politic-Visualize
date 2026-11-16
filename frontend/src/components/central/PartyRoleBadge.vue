<script setup lang="ts">
import { computed } from "vue";
import { useAppStore } from "@/stores/app";
import type { CentralPartyRole } from "@/types";

const props = defineProps<{ roles: CentralPartyRole[]; compact?: boolean }>();
const app = useAppStore();
const sorted = computed(() => {
  const order: Record<CentralPartyRole["role"], number> = {
    politburo_standing: 0,
    politburo_member: 1,
    secretariat_member: 2,
    discipline_secretary: 3,
    military_chair: 4,
    military_vice_chair: 5,
    military_member: 6,
  };
  return [...(props.roles ?? [])].sort((a, b) => order[a.role] - order[b.role]);
});
const statusText = (role: CentralPartyRole): string =>
  app.vocabulary?.identity_status[role.status] ?? role.status;
const tone = (role: CentralPartyRole) => {
  if (role.status === "expelled") return "border-vermilion/70 text-vermilion-bright bg-vermilion/10";
  if (role.role === "politburo_standing") return "border-vermilion/55 text-vermilion-bright bg-vermilion/[0.08]";
  if (role.role === "politburo_member") return "border-gold/45 text-gold bg-gold/[0.07]";
  if (role.role === "discipline_secretary") return "border-violet-400/60 text-violet-300 bg-violet-400/[0.08]";
  if (role.role.startsWith("military_")) return "border-sky-400/60 text-sky-300 bg-sky-400/[0.08]";
  return "border-jade/35 text-jade bg-jade/[0.06]";
};
</script>

<template>
  <template v-for="role in sorted" :key="role.role">
    <span
      class="inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[9px] leading-none"
      :class="[tone(role), compact ? 'px-1' : '']"
    >
      {{ role.label }}
      <span v-if="role.status !== 'active'" class="opacity-80">· {{ statusText(role) }}</span>
    </span>
  </template>
</template>
