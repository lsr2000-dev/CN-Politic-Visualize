<script setup lang="ts">
import { computed } from "vue";
import AppIcon from "../ui/AppIcon.vue";
import TeamSection from "./TeamSection.vue";
import ProvinceTimeline from "./ProvinceTimeline.vue";
import CompareTray from "./CompareTray.vue";
import { useMapStore } from "@/stores/map";
import { useTimelineStore } from "@/stores/timeline";
import { useOfficerStore } from "@/stores/app";
import { formatDate, formatDuration } from "@/utils/format";
import type { CategoryKey, Member, ViewMode } from "@/types";

const props = defineProps<{ mode: ViewMode }>();
const emit = defineEmits<{ (event: "close"): void }>();

const map = useMapStore();
const timeline = useTimelineStore();
const officer = useOfficerStore();

const region = computed(() => map.selectedRegion);
const order: CategoryKey[] = ["party", "congress", "government", "cppcc"];
const teams = computed(() => {
  if (!region.value) return [];
  return order.map((key) => region.value!.teams[key as keyof typeof region.value.teams]);
});
const syncing = computed(
  () => map.loading || (map.snapshot !== null && map.snapshot.as_of !== timeline.currentDate),
);
const pinned = computed(() => map.isPinned(region.value?.region_code ?? null));

function selectMember(member: Member): void {
  if (!region.value) return;
  void officer.openOfficer(member.officer.id, timeline.currentDate);
}

function openSeat(member: Member): void {
  if (!region.value) return;
  void officer.openSeat(
    {
      regionCode: region.value.region_code,
      regionName: region.value.region_name,
      seatKey: member.seat_key,
      title: member.title,
      category: member.category,
    },
    timeline.currentDate,
  );
}

function togglePin(): void {
  if (region.value) map.togglePin(region.value.region_code);
}
</script>

<template>
  <div class="flex h-full min-h-0 flex-col">
    <div v-if="region" class="flex h-full min-h-0 flex-col">
      <header class="relative shrink-0 overflow-hidden border-b border-white/[0.07] px-5 pb-4 pt-5">
        <div
          class="pointer-events-none absolute -right-10 -top-14 h-40 w-40 rounded-full bg-[radial-gradient(circle,rgba(200,73,47,0.14),transparent_65%)]"
        />
        <div class="relative flex items-start justify-between gap-3">
          <div class="min-w-0">
            <div class="flex items-center gap-2">
              <span class="h-3 w-[2px] bg-vermilion" />
              <span class="label-eyebrow">PROVINCIAL SNAPSHOT</span>
            </div>
            <h1
              class="mt-1.5 truncate font-display leading-none tracking-wide text-paper"
              :class="props.mode === 'fullscreen' ? 'text-[38px]' : 'text-[30px]'"
            >
              {{ region.region_name }}
            </h1>
            <div class="mt-2.5 flex flex-wrap items-center gap-1.5">
              <span class="chip tabular-nums">{{ region.region_code }}</span>
              <span class="chip">{{ region.filled }}/4 班子收录</span>
              <span class="chip">{{ region.member_count }} 人在任</span>
              <span
                v-if="syncing"
                class="inline-flex items-center gap-1 rounded-full border border-vermilion/25 bg-vermilion/10 px-2 py-0.5 text-[9px] text-vermilion-bright"
              >
                <span class="h-1 w-1 rounded-full bg-vermilion live-dot" />
                同步中
              </span>
            </div>
          </div>
          <div class="flex shrink-0 items-center gap-1" data-no-drag>
            <button
              class="btn-icon"
              :class="pinned ? 'border-vermilion/40 bg-vermilion/10 text-vermilion-bright' : ''"
              :title="pinned ? '取消钉住' : '钉住以对比'"
              :aria-pressed="pinned"
              @click="togglePin"
            >
              <AppIcon name="pin" :size="14" />
            </button>
            <button class="btn-icon" title="关闭面板" aria-label="关闭面板" @click="emit('close')">
              <AppIcon name="close" :size="15" />
            </button>
          </div>
        </div>

        <div class="relative mt-4 grid grid-cols-2 divide-x divide-y divide-white/[0.07] rounded-lg border border-white/[0.07] bg-white/[0.02] sm:grid-cols-4 sm:divide-y-0">
          <div class="px-2.5 py-2">
            <div class="label-eyebrow">书记在任</div>
            <div class="mt-1 truncate text-[11px] text-paper-dim">
              <template v-if="region.headline.party?.is_roster_snapshot && region.metrics.party_days > 0">
                约 {{ formatDuration(region.metrics.party_days) }}
              </template>
              <template v-else-if="region.headline.party?.is_roster_snapshot">起始待考</template>
              <template v-else>{{ formatDuration(region.metrics.party_days) }}</template>
            </div>
          </div>
          <div class="px-2.5 py-2">
            <div class="label-eyebrow">省长在任</div>
            <div class="mt-1 truncate text-[11px] text-paper-dim">
              <template v-if="region.headline.government?.is_roster_snapshot && region.metrics.governor_days > 0">
                约 {{ formatDuration(region.metrics.governor_days) }}
              </template>
              <template v-else-if="region.headline.government?.is_roster_snapshot">起始待考</template>
              <template v-else>{{ formatDuration(region.metrics.governor_days) }}</template>
            </div>
          </div>
          <div class="px-2.5 py-2">
            <div class="label-eyebrow">书记人数</div>
            <div class="mt-1 text-[11px] tabular-nums text-paper-dim">
              {{ region.metrics.party_count }} 人
            </div>
          </div>
          <div class="px-2.5 py-2">
            <div class="label-eyebrow">代理在任</div>
            <div class="mt-1 text-[11px] tabular-nums" :class="region.acting_count ? 'text-vermilion-bright' : 'text-paper-dim'">
              {{ region.acting_count }} 人
            </div>
          </div>
        </div>
        <p class="relative mt-2.5 flex items-center gap-1.5 text-[10px] text-paper-faint">
          <AppIcon name="calendar" :size="11" />
          {{ formatDate(map.snapshot?.as_of ?? timeline.currentDate, "YYYY.MM.DD") }} 快照
          <span class="h-2.5 w-px bg-white/10" />
          点击官员查看履历，点击「历任」查看席位沿革
        </p>
      </header>

      <div class="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-4">
        <div
          class="rise"
          :class="props.mode === 'fullscreen' ? 'mx-auto grid w-full max-w-[1280px] gap-3 md:grid-cols-2' : 'space-y-2.5'"
        >
          <TeamSection
            v-for="team in teams"
            :key="team.key"
            :team="team"
            :default-open="true"
            @select="selectMember"
            @history="openSeat"
          />
        </div>

        <div v-if="props.mode === 'fullscreen'" class="mx-auto mt-4 w-full max-w-[1280px]">
          <ProvinceTimeline :region-code="region.region_code" />
        </div>

        <div class="mt-4 flex items-start gap-1.5 px-1 text-[9px] leading-relaxed text-paper-faint/70">
          <AppIcon name="info" :size="10" class="mt-px shrink-0" />
          <span>演示数据，月份级精度；部分任职日期依据公开报道推定，生产使用前须逐条复核。</span>
        </div>
      </div>

      <CompareTray />
    </div>

    <div v-else class="flex h-full flex-col">
      <div class="flex items-center justify-between border-b border-white/[0.07] px-5 py-4">
        <span class="label-eyebrow">PROVINCIAL SNAPSHOT</span>
        <button class="btn-icon" aria-label="关闭面板" @click="emit('close')">
          <AppIcon name="close" :size="15" />
        </button>
      </div>
      <div class="min-h-0 flex-1">
        <slot name="empty" />
      </div>
      <CompareTray />
    </div>
  </div>
</template>
