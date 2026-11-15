<script setup lang="ts">
import { computed } from "vue";
import type { CentralPartyRole } from "@/types";

const props = defineProps<{ roles: CentralPartyRole[]; compact?: boolean }>();
const sorted = computed(() => {
  const order: Record<CentralPartyRole["role"], number> = { politburo_standing: 0, politburo_member: 1, secretariat_member: 2 };
  return [...(props.roles ?? [])].sort((a, b) => order[a.role] - order[b.role]);
});
const tone = (role: CentralPartyRole) => {
  if (role.status === "expelled") return "border-vermilion/70 text-vermilion-bright bg-vermilion/10";
  if (role.role === "politburo_standing") return "border-vermilion/55 text-vermilion-bright bg-vermilion/[0.08]";
  if (role.role === "politburo_member") return "border-gold/45 text-gold bg-gold/[0.07]";
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
      <span v-if="role.status !== 'active'" class="opacity-80">· {{ role.status === "expelled" ? "已开除" : "已结束" }}</span>
    </span>
  </template>
</template>
