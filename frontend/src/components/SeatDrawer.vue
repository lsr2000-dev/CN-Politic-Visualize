<script setup lang="ts">
import { computed } from "vue";
import AppIcon from "./ui/AppIcon.vue";
import { useOfficerStore } from "@/stores/app";
import { useTimelineStore } from "@/stores/timeline";
import { categoryColor, formatDate, formatDuration, initials } from "@/utils/format";

const officer = useOfficerStore();
const timeline = useTimelineStore();

const seat = computed(() => officer.seatHistory);
const context = computed(() => officer.activeSeat);
const color = computed(() => categoryColor(seat.value?.category ?? context.value?.category ?? "other"));

function openPerson(officerId: number): void {
  void officer.openOfficer(officerId, timeline.currentDate);
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="officer.activeSeat"
        class="fixed inset-0 z-[55] bg-ink-950/65 backdrop-blur-[2px]"
        @click.self="officer.closeSeat()"
      >
        <Transition name="drawer" appear>
          <aside
            class="absolute right-0 top-0 flex h-full w-[min(580px,100vw)] flex-col border-l border-white/10 bg-ink-900 shadow-panel"
            role="dialog"
            aria-label="席位沿革"
          >
            <div class="flex shrink-0 items-start justify-between border-b border-white/[0.08] px-6 py-4">
              <div class="min-w-0">
                <div class="flex items-center gap-2">
                  <span class="h-3 w-[2px]" :style="{ backgroundColor: color }" />
                  <span class="label-eyebrow">SEAT LINEAGE / 席位沿革</span>
                </div>
                <h2 class="mt-1.5 truncate font-display text-[24px] leading-tight tracking-wide text-paper">
                  {{ context?.regionName }} · {{ seat?.title ?? context?.title }}
                </h2>
                <div class="mt-2 flex items-center gap-1.5">
                  <span class="chip">{{ context?.regionCode }}</span>
                  <span class="chip">{{ seat ? `${seat.holder_count} 人曾任` : "载入中" }}</span>
                  <span v-if="seat?.acting_count" class="chip border-vermilion/30 text-vermilion-bright">
                    {{ seat.acting_count }} 次代理
                  </span>
                </div>
              </div>
              <button class="btn-icon shrink-0" aria-label="关闭席位沿革" @click="officer.closeSeat()">
                <AppIcon name="close" :size="16" />
              </button>
            </div>

            <div class="min-h-0 flex-1 overflow-y-auto overscroll-contain px-6 py-5">
              <div v-if="officer.loadingSeat" class="space-y-4">
                <div v-for="index in 4" :key="index" class="flex gap-3">
                  <div class="skeleton h-3 w-14 rounded" />
                  <div class="skeleton h-16 flex-1 rounded-lg" />
                </div>
              </div>

              <div v-else-if="officer.seatError" class="py-16 text-center">
                <AppIcon name="info" :size="22" class="mx-auto text-vermilion-bright" />
                <p class="mt-3 text-[12px] text-paper">席位数据加载失败</p>
                <p class="mt-1 text-[10px] text-paper-faint">{{ officer.seatError }}</p>
              </div>

              <template v-else-if="seat">
                <div class="mb-4 grid grid-cols-3 divide-x divide-white/[0.07] rounded-lg border border-white/[0.07] bg-white/[0.02]">
                  <div class="px-3 py-2.5">
                    <div class="label-eyebrow">现任</div>
                    <div class="mt-1 truncate text-[11px] text-paper-dim">
                      {{ seat.incumbent?.officer.name ?? "空缺 / 未收录" }}
                    </div>
                  </div>
                  <div class="px-3 py-2.5">
                    <div class="label-eyebrow">历任人数</div>
                    <div class="mt-1 text-[13px] tabular-nums text-paper">{{ seat.holder_count }}</div>
                  </div>
                  <div class="px-3 py-2.5">
                    <div class="label-eyebrow">代理次数</div>
                    <div class="mt-1 text-[13px] tabular-nums" :class="seat.acting_count ? 'text-vermilion-bright' : 'text-paper'">
                      {{ seat.acting_count }}
                    </div>
                  </div>
                </div>

                <div class="relative">
                  <div
                    v-for="span in seat.spans"
                    :key="span.tenure_id"
                    class="grid grid-cols-[58px_16px_1fr] gap-2"
                  >
                    <div class="pt-2.5 text-right">
                      <div class="text-[9px] tabular-nums text-paper-faint">{{ formatDate(span.start_date, "YYYY.MM") }}</div>
                      <div class="mt-0.5 text-[8px] tabular-nums text-paper-faint/60">
                        {{ span.end_date ? formatDate(span.end_date, "YYYY.MM") : "至今" }}
                      </div>
                    </div>

                    <div class="relative flex justify-center">
                      <span class="absolute inset-y-0 w-px bg-white/10" />
                      <span
                        class="relative mt-3 h-2.5 w-2.5 rounded-full border-2"
                        :class="span.is_acting ? 'bg-ink-900' : ''"
                        :style="{ borderColor: color, backgroundColor: span.is_acting ? '#0d1117' : color }"
                      />
                    </div>

                    <div class="pb-2.5">
                      <div
                        v-if="span.gap_before_days && span.gap_before_days > 30"
                        class="mb-1.5 flex items-center gap-2 pl-1 text-[9px] text-paper-faint/70"
                      >
                        <span class="h-px w-4 border-t border-dashed border-white/20" />
                        空缺 {{ formatDuration(span.gap_before_days) }}
                      </div>
                      <button
                        class="group w-full rounded-lg border px-3 py-2.5 text-left transition"
                        :class="span.is_future
                          ? 'border-dashed border-white/10 bg-white/[0.01] opacity-70 hover:opacity-100'
                          : span.is_current
                            ? 'border-vermilion/25 bg-vermilion/[0.06] hover:border-vermilion/45'
                            : 'border-white/[0.07] bg-white/[0.02] hover:border-white/20 hover:bg-white/[0.04]'"
                        @click="openPerson(span.officer_id)"
                      >
                        <div class="flex items-center gap-2">
                          <span
                            class="flex h-7 w-7 items-center justify-center rounded border border-white/10 bg-white/[0.03] font-display text-[11px] text-paper-dim"
                          >
                            {{ initials(span.officer_name) }}
                          </span>
                          <span class="text-[13px] text-paper">{{ span.officer_name }}</span>
                          <span
                            v-if="span.is_acting"
                            class="rounded border border-vermilion/40 px-1 py-px text-[8px] text-vermilion-bright"
                          >
                            代理
                          </span>
                          <span v-if="span.is_future" class="rounded border border-white/10 px-1 py-px text-[8px] text-paper-faint">
                            此后任职
                          </span>
                          <span v-else-if="span.is_current" class="rounded bg-vermilion/15 px-1 py-px text-[8px] text-vermilion-bright">
                            在任
                          </span>
                          <span class="ml-auto text-[9px] tabular-nums text-paper-faint">
                            <template v-if="span.is_future || (span.start_precision === 'snapshot' && span.duration_days <= 0)">—</template>
                            <template v-else-if="span.start_precision === 'snapshot'">约 {{ formatDuration(span.duration_days) }}</template>
                            <template v-else>{{ formatDuration(span.duration_days) }}</template>
                          </span>
                        </div>
                        <div class="mt-1.5 min-w-0 pl-9 text-[9px] text-paper-faint">
                          <div class="whitespace-normal break-words leading-snug">{{ span.title }}</div>
                          <div class="mt-1 flex flex-wrap items-center gap-2">
                            <span class="shrink-0 whitespace-nowrap rounded border border-white/10 px-1 py-px text-[8px] text-paper-faint">{{ span.rank_label }}</span>
                            <span class="h-2 w-px shrink-0 bg-white/10" />
                            <span v-if="span.start_precision === 'snapshot' && span.duration_days > 0" class="shrink-0 text-gold">
                              约 {{ formatDate(span.start_date, "YYYY.MM") }} 起
                            </span>
                            <span v-else-if="span.start_precision === 'snapshot'" class="shrink-0 text-gold">现任（起始待考）</span>
                            <span v-else class="shrink-0 tabular-nums">
                              {{ formatDate(span.start_date, "YYYY.MM.DD") }} —
                              {{ span.end_date ? formatDate(span.end_date, "YYYY.MM.DD") : "至今" }}
                            </span>
                            <span v-if="span.is_future" class="shrink-0 text-gold">尚未到任</span>
                            <span v-if="span.event_label" class="shrink-0 text-vermilion-bright/90">
                              · {{ span.event_date ? formatDate(span.event_date, "YYYY.MM") : "" }} {{ span.event_label }}
                            </span>
                            <span v-else-if="span.exit_reason_label" class="shrink-0 text-vermilion-bright/80">
                              · {{ span.exit_reason_label }}
                            </span>
                          </div>
                        </div>
                      </button>
                    </div>
                  </div>
                </div>

                <p class="mt-2 flex items-start gap-1.5 text-[9px] leading-relaxed text-paper-faint/70">
                  <AppIcon name="info" :size="10" class="mt-px shrink-0" />
                  代理记录以空心节点标示；间隔超过 30 天的空档显示为「空缺」。点击任一记录查看官员完整履历。
                </p>
              </template>
            </div>
          </aside>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>
