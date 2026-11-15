<script setup lang="ts">
import { ref } from "vue";
import AppIcon from "../ui/AppIcon.vue";
import LeaderRow from "./LeaderRow.vue";
import { categoryColor } from "@/utils/format";
import type { Member, Team } from "@/types";

const props = withDefaults(
  defineProps<{ team: Team; defaultOpen?: boolean; capacity?: number }>(),
  { defaultOpen: true, capacity: 1 },
);
defineEmits<{ (event: "select", member: Member): void; (event: "history", member: Member): void }>();

const open = ref(props.defaultOpen);
const color = categoryColor(props.team.key);

const english: Record<string, string> = {
  party: "PARTY",
  congress: "CONGRESS",
  government: "GOVERNMENT",
  cppcc: "CPPCC",
  other: "OTHER",
};
</script>

<template>
  <section class="overflow-hidden rounded-xl border border-white/[0.07] bg-white/[0.015]">
    <button
      class="flex w-full items-center gap-2.5 px-3 py-2.5 text-left transition hover:bg-white/[0.03]"
      :aria-expanded="open"
      @click="open = !open"
    >
      <span class="h-3.5 w-[2px] rounded-full" :style="{ backgroundColor: color }" />
      <span class="text-[12px] tracking-[0.12em] text-paper">{{ team.label }}</span>
      <span class="text-[9px] tracking-[0.18em] text-paper-faint">{{ english[team.key] }}</span>
      <span
        class="ml-1 rounded-full px-1.5 py-px text-[9px] tabular-nums"
        :style="{ backgroundColor: `${color}1a`, color }"
      >
        {{ team.members.length }}
      </span>
      <span
        v-if="team.members.length === 0"
        class="ml-auto text-[9px] text-paper-faint"
      >待收录</span>
      <AppIcon
        v-else
        name="chevron-down"
        :size="13"
        class="ml-auto text-paper-faint transition-transform duration-300"
        :class="open ? 'rotate-0' : '-rotate-90'"
      />
    </button>

    <div v-show="open" class="border-t border-white/[0.05] px-1.5 py-1.5">
      <template v-if="team.members.length">
        <LeaderRow
          v-for="(member, index) in team.members"
          :key="member.tenure_id"
          :member="member"
          :lead="index === 0"
          @select="$emit('select', $event)"
          @history="$emit('history', $event)"
        />
      </template>
      <div
        v-else
        class="mx-1 mb-1 flex items-center justify-between rounded-lg border border-dashed border-white/10 px-3 py-3"
      >
        <span class="text-[10px] text-paper-faint">该日期暂无{{ team.label }}主官记录</span>
        <span class="text-[9px] tracking-widest text-paper-faint/60">NO DATA</span>
      </div>
    </div>
  </section>
</template>
