<script setup lang="ts">
import { computed } from "vue";
import AppIcon from "../ui/AppIcon.vue";
import { categoryColor, formatDuration, formatMonth, initials } from "@/utils/format";
import type { Member } from "@/types";

const props = defineProps<{ member: Member; lead?: boolean }>();
defineEmits<{ (event: "select", member: Member): void; (event: "history", member: Member): void }>();

const color = computed(() => categoryColor(props.member.category));
const progress = computed(() => Math.min(100, (props.member.duration_days / 3650) * 100));
const snapshotDuration = computed(() => props.member.start_precision === "snapshot" && props.member.duration_days > 0);
const durationText = computed(() => {
  if (props.member.is_future) return "—";
  if (props.member.start_precision === "snapshot" && props.member.duration_days <= 0) return "—";
  if (snapshotDuration.value) return `约 ${formatDuration(props.member.duration_days)}`;
  return formatDuration(props.member.duration_days);
});
</script>

<template>
  <div
    class="group relative flex cursor-pointer items-center gap-2.5 rounded-lg px-2 py-1.5 transition-colors duration-200 hover:bg-white/[0.05] focus-visible:bg-white/[0.05] focus-visible:outline-none"
    role="button"
    tabindex="0"
    :aria-label="`${member.officer.name}，${member.title}`"
    @click="$emit('select', member)"
    @keydown.enter.prevent="$emit('select', member)"
    @keydown.space.prevent="$emit('select', member)"
  >
    <div
      class="flex shrink-0 items-center justify-center rounded-md border font-display transition-transform duration-300 group-hover:scale-[1.04]"
      :class="lead ? 'h-10 w-10 text-[15px]' : 'h-8 w-8 text-[13px]'"
      :style="{
        backgroundColor: `${color}1f`,
        borderColor: `${color}55`,
        color,
      }"
    >
      {{ initials(member.officer.name) }}
    </div>

    <div class="min-w-0 flex-1">
      <div class="flex items-center gap-1.5">
        <span
          class="truncate font-medium text-paper"
          :class="lead ? 'text-[13.5px]' : 'text-[12px]'"
        >
          {{ member.officer.name }}
        </span>
        <span
          v-if="member.is_acting"
          class="shrink-0 rounded border border-vermilion/45 bg-vermilion/10 px-1 py-px text-[9px] leading-tight text-vermilion-bright"
        >
          代理
        </span>
        <span
          v-if="member.is_provisional"
          class="shrink-0 rounded border border-gold/35 bg-gold/10 px-1 py-px text-[9px] leading-tight text-gold"
        >
          待更新
        </span>
        <span
          v-if="member.is_concurrent"
          class="shrink-0 rounded border border-white/15 px-1 py-px text-[9px] leading-tight text-paper-faint"
        >
          兼任
        </span>
      </div>
      <div class="mt-1 min-w-0 text-[10px] text-paper-faint">
        <div class="whitespace-normal break-words leading-snug">
          <button
            type="button"
            class="text-left text-paper-faint underline decoration-white/25 decoration-dotted underline-offset-2 transition hover:text-paper hover:decoration-gold/60"
            title="查看该岗位历任"
            @click.stop="$emit('history', member)"
          >
            {{ member.title }}
          </button>
        </div>
        <div class="mt-1 flex flex-wrap items-center gap-1.5">
          <span class="shrink-0 whitespace-nowrap rounded border border-white/10 px-1 py-px text-[8px] text-paper-faint">
            {{ member.rank_label }}
          </span>
          <span class="h-2.5 w-px shrink-0 bg-white/10" />
          <span v-if="member.start_precision === 'snapshot' && member.duration_days > 0" class="shrink-0 text-gold">约 {{ formatMonth(member.start_date) }} 起</span>
          <span v-else-if="member.start_precision === 'snapshot'" class="shrink-0 text-gold">现任 · 起始待考</span>
          <span v-else class="shrink-0 tabular-nums">
            任职 {{ formatMonth(member.start_date) }} — {{ member.end_date ? formatMonth(member.end_date) : "至今" }}
          </span>
          <span
            v-if="member.is_future"
            class="shrink-0 whitespace-nowrap rounded border border-dashed border-gold/35 px-1 py-px text-[8px] text-gold/80"
          >
            尚未到任
          </span>
        </div>
      </div>
    </div>

    <div class="shrink-0 text-right">
      <div class="text-[10px] tabular-nums text-paper-dim">
        {{ durationText }}
      </div>
      <div class="ml-auto mt-1 h-[2px] w-14 overflow-hidden rounded-full bg-white/10">
        <div class="h-full rounded-full" :style="{ width: `${progress}%`, backgroundColor: color }" />
      </div>
    </div>

    <button
      class="ml-0.5 hidden shrink-0 items-center gap-0.5 rounded px-1.5 py-1 text-[9px] text-paper-faint transition hover:bg-white/10 hover:text-paper group-hover:flex"
      title="查看该席位历任"
      @click.stop="$emit('history', member)"
    >
      历任
      <AppIcon name="chevron-right" :size="10" />
    </button>
  </div>
</template>
