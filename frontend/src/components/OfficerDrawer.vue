<script setup lang="ts">
import { computed, watch } from "vue";
import AppIcon from "./ui/AppIcon.vue";
import CareerGantt from "./charts/CareerGantt.vue";
import CentralCommitteeBadge from "./central/CentralCommitteeBadge.vue";
import PartyRoleBadge from "./central/PartyRoleBadge.vue";
import { showCentralCommittee, visiblePartyRoles } from "@/utils/partyRoles";
import { useOfficerStore } from "@/stores/app";
import { useCentralStore } from "@/stores/central";
import { useTimelineStore } from "@/stores/timeline";
import { ageOf, categoryColor, formatDate, formatMonth, initials } from "@/utils/format";
import type { Member } from "@/types";

const officer = useOfficerStore();
const central = useCentralStore();
const timeline = useTimelineStore();

const profile = computed(() => officer.profile);
const person = computed(() => profile.value?.officer ?? null);
const career = computed(() => officer.career);

const committee = computed(() =>
  person.value ? central.committeeFor(person.value.name, timeline.currentDate) : null,
);
const partyRoles = computed(() =>
  person.value ? central.partyRolesFor(person.value.name, timeline.currentDate) : [],
);
watch(
  () => [person.value?.name, timeline.currentDate] as const,
  ([name, day]) => {
    if (name) void central.loadCommittee(name, day);
  },
  { immediate: true },
);

const age = computed(() =>
  person.value ? ageOf(person.value.birth_year, career.value?.range.to ?? timeline.currentDate) : null,
);

const currentPositions = computed<Member[]>(() => profile.value?.current ?? []);

const facts = computed(() => {  if (!person.value) return [];
  const items = [
    ["出生", person.value.birth_year ? `${person.value.birth_year} 年` : "待补充"],
    ["性别", person.value.gender === "F" ? "女" : person.value.gender === "M" ? "男" : "待补充"],
    ["籍贯", person.value.native_place ?? "待补充"],
    ["民族", person.value.ethnicity ?? "待补充"],
    ["入党", person.value.party_join_date ? formatMonth(person.value.party_join_date) : "待补充"],
    ["参加工作", person.value.work_start_date ? formatMonth(person.value.work_start_date) : "待补充"],
    ["学历", [person.value.education, person.value.degree].filter(Boolean).join(" / ") || "待补充"],
  ];
  return items;
});

const legend = [
  { key: "party", label: "党委" },
  { key: "congress", label: "人大" },
  { key: "government", label: "政府" },
  { key: "cppcc", label: "政协" },
];

const events = computed(() => profile.value?.events ?? []);
const previousPosition = computed(() => profile.value?.previous ?? null);
const nextPosition = computed(() => profile.value?.next ?? null);

function statusClass(status: string | undefined): string {
  switch (status) {
    case "active":
      return "border-jade/35 bg-jade/10 text-jade";
    case "under_investigation":
      return "border-gold/40 bg-gold/10 text-gold";
    case "expelled":
      return "border-vermilion/40 bg-vermilion/10 text-vermilion-bright";
    case "retired":
      return "border-white/15 bg-white/[0.04] text-paper-dim";
    case "deceased":
      return "border-white/10 bg-white/[0.03] text-paper-faint";
    default:
      return "border-white/10 bg-white/[0.02] text-paper-faint";
  }
}

function contextPeriod(member: Member | null): string {
  if (!member) return "";
  const start = member.start_precision === "snapshot"
    ? "起始待考"
    : formatDate(member.start_date, "YYYY.MM");
  return `${start} — ${member.end_date ? formatDate(member.end_date, "YYYY.MM") : "至今"}`;
}

function openSeat(member: Member): void {
  if (!member.region_code || !member.region_name) return;
  void officer.openSeat(
    {
      regionCode: member.region_code,
      regionName: member.region_name,
      seatKey: member.seat_key,
      title: member.title,
      category: member.category,
    },
    timeline.currentDate,
  );
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="officer.activeOfficerId !== null"
        class="fixed inset-0 z-[86] bg-ink-950/65 backdrop-blur-[2px]"
        @click.self="officer.closeOfficer()"
      >
        <Transition name="drawer" appear>
          <aside
            class="absolute right-0 top-0 flex h-full w-[min(800px,100vw)] flex-col border-l border-white/10 bg-ink-900 shadow-panel"
            role="dialog"
            aria-label="官员档案"
          >
            <div class="flex shrink-0 items-center justify-between border-b border-white/[0.08] px-6 py-3.5 sm:px-8">
              <div class="flex items-center gap-2">
                <span class="h-3 w-[2px] bg-vermilion" />
                <span class="label-eyebrow">OFFICER DOSSIER / 官员档案</span>
              </div>
              <button class="btn-icon" aria-label="关闭官员档案" @click="officer.closeOfficer()">
                <AppIcon name="close" :size="16" />
              </button>
            </div>

            <div class="min-h-0 flex-1 overflow-y-auto overscroll-contain">
              <!-- loading -->
              <div v-if="!person && officer.loadingProfile" class="px-6 py-8 sm:px-8">
                <div class="flex gap-5">
                  <div class="skeleton h-16 w-16 rounded-lg" />
                  <div class="flex-1 space-y-3">
                    <div class="skeleton h-8 w-40 rounded" />
                    <div class="skeleton h-3 w-64 rounded" />
                  </div>
                </div>
                <div class="mt-8 space-y-2">
                  <div class="skeleton h-3 w-full rounded" />
                  <div class="skeleton h-3 w-5/6 rounded" />
                  <div class="skeleton h-3 w-2/3 rounded" />
                </div>
                <div class="mt-10 h-40 rounded-lg border border-white/[0.06] bg-white/[0.02]" />
              </div>

              <!-- error -->
              <div v-else-if="officer.error && !person" class="flex flex-col items-center justify-center px-8 py-24 text-center">
                <AppIcon name="info" :size="24" class="text-vermilion-bright" />
                <p class="mt-3 text-sm text-paper">档案加载失败</p>
                <p class="mt-1 text-[11px] text-paper-faint">{{ officer.error }}</p>
                <button class="btn-ghost mt-4" @click="officer.activeOfficerId && officer.openOfficer(officer.activeOfficerId, timeline.currentDate)">
                  重试
                </button>
              </div>

              <template v-else-if="person">
                <!-- identity -->
                <div class="relative overflow-hidden px-6 pb-6 pt-6 sm:px-8">
                  <div class="pointer-events-none absolute -right-20 -top-24 h-64 w-64 rounded-full bg-[radial-gradient(circle,rgba(200,73,47,.13),transparent_65%)]" />
                  <div class="relative flex items-start gap-4 sm:gap-5">
                    <div
                      class="flex h-16 w-16 shrink-0 items-center justify-center rounded-lg border border-vermilion/30 bg-vermilion/[0.08] font-display text-2xl text-vermilion-bright"
                    >
                      {{ initials(person.name) }}
                    </div>
                    <div class="min-w-0 flex-1">
                      <div class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                        <h2 class="font-display text-[34px] leading-none tracking-wide text-paper">
                          {{ person.name }}
                        </h2>
                        <span v-if="age" class="text-[11px] text-paper-faint">{{ age }} 岁</span>
                        <PartyRoleBadge :roles="visiblePartyRoles(partyRoles)" />
                        <CentralCommitteeBadge
                          v-if="showCentralCommittee(partyRoles) || !partyRoles.length"
                          :committee="committee"
                        />
                        <span v-if="committee?.status_note" class="text-[9px] leading-snug text-paper-faint">
                          {{ committee.status_note }}
                        </span> 
                        <span v-if="person.gender" class="text-[11px] text-paper-faint">
                          {{ person.gender === "F" ? "女" : "男" }}
                        </span>
                        <span
                          v-if="profile"
                          class="rounded-full border px-2 py-0.5 text-[9px]"
                          :class="statusClass(profile.status)"
                        >
                          {{ profile.status_label }}
                        </span>
                      </div>
                      <div class="mt-2.5 flex flex-wrap items-center gap-1.5">
                        <span
                          v-for="member in currentPositions.slice(0, 4)"
                          :key="`${member.tenure_id}`"
                          class="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/[0.04] px-2 py-0.5 text-[10px] text-paper-dim"
                        >
                          <span class="h-1 w-1 rounded-full" :style="{ backgroundColor: categoryColor(member.category) }" />
                          {{ member.region_short_name ? `${member.region_short_name} · ` : "" }}{{ member.title }}
                        </span>
                        <span v-if="!currentPositions.length" class="chip">当前无在任记录</span>
                      </div>
                    </div>
                  </div>

                  <p v-if="person.bio" class="relative mt-5 max-w-[640px] text-[12px] leading-7 text-paper-dim">
                    {{ person.bio }}
                  </p>

                  <div class="relative mt-5 grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-3">
                    <div v-for="item in facts" :key="item[0]" class="flex items-baseline gap-2 border-b border-white/[0.05] pb-1.5">
                      <span class="w-14 shrink-0 text-[9px] tracking-wider text-paper-faint">{{ item[0] }}</span>
                      <span class="truncate text-[11px] text-paper-dim">{{ item[1] }}</span>
                    </div>
                  </div>

                  <div v-if="career" class="relative mt-5 grid grid-cols-4 divide-x divide-white/[0.07] rounded-lg border border-white/[0.07] bg-white/[0.02]">
                    <div class="px-3 py-2.5">
                      <div class="label-eyebrow">任职段</div>
                      <div class="mt-1 font-display text-lg leading-none text-paper tabular-nums">{{ career.summary.span_count }}</div>
                    </div>
                    <div class="px-3 py-2.5">
                      <div class="label-eyebrow">跨省</div>
                      <div class="mt-1 font-display text-lg leading-none text-paper tabular-nums">{{ career.summary.province_count }}</div>
                    </div>
                    <div class="px-3 py-2.5">
                      <div class="label-eyebrow">代理</div>
                      <div class="mt-1 font-display text-lg leading-none text-paper tabular-nums">{{ career.summary.acting_count }}</div>
                    </div>
                    <div class="px-3 py-2.5">
                      <div class="label-eyebrow">观察区间</div>
                      <div class="mt-1 text-[10px] tabular-nums text-paper-dim">
                        {{ formatDate(career.range.from, "YYYY") }}—{{ formatDate(career.range.to, "YYYY") }}
                      </div>
                    </div>
                  </div>

                  <div class="relative mt-4 grid gap-2 sm:grid-cols-2">
                    <div class="rounded-lg border border-white/[0.07] bg-white/[0.02] p-3">
                      <div class="label-eyebrow">任职前 / PREVIOUS</div>
                      <template v-if="previousPosition">
                        <div class="mt-1.5 truncate text-[12px] text-paper">{{ previousPosition.title }}</div>
                        <div class="mt-1 text-[9px] text-paper-faint">
                          {{ previousPosition.region_name ?? "中央机构" }} · {{ previousPosition.rank_label }}
                          <span class="mx-1 text-white/15">|</span>{{ contextPeriod(previousPosition) }}
                        </div>
                      </template>
                      <p v-else class="mt-1.5 text-[10px] text-paper-faint/70">暂无更早的公开任职记录</p>
                    </div>
                    <div class="rounded-lg border border-white/[0.07] bg-white/[0.02] p-3">
                      <div class="label-eyebrow">离任后 / NEXT</div>
                      <template v-if="nextPosition">
                        <div class="mt-1.5 truncate text-[12px] text-paper">{{ nextPosition.title }}</div>
                        <div class="mt-1 text-[9px] text-paper-faint">
                          {{ nextPosition.region_name ?? "中央机构" }} · {{ nextPosition.rank_label }}
                          <span class="mx-1 text-white/15">|</span>{{ contextPeriod(nextPosition) }}
                        </div>
                      </template>
                      <p v-else class="mt-1.5 text-[10px]" :class="profile?.status === 'active' ? 'text-jade' : 'text-paper-faint'">
                        {{ profile?.status === "active" ? "现任，暂无后续任职" : (profile?.status_label ?? "待补充") }}
                      </p>
                    </div>
                  </div>

                  <div v-if="events.length" class="relative mt-3 rounded-lg border border-white/[0.07] bg-white/[0.015] p-3">
                    <div class="label-eyebrow">状态与去向 / STATUS EVENTS</div>
                    <div class="mt-2 space-y-2">
                      <div v-for="event in events" :key="event.id" class="flex gap-3 border-l border-white/10 pl-3">
                        <div class="w-14 shrink-0 text-[9px] tabular-nums text-paper-faint">
                          {{ formatDate(event.event_date, "YYYY.MM") }}
                        </div>
                        <div class="min-w-0 flex-1">
                          <div class="flex flex-wrap items-center gap-2">
                            <span class="text-[11px] text-paper">{{ event.title }}</span>
                            <span v-if="event.verified" class="rounded border border-jade/30 px-1 text-[8px] text-jade">已核</span>
                          </div>
                          <p v-if="event.description" class="mt-0.5 text-[9px] leading-relaxed text-paper-faint">
                            {{ event.description }}
                          </p>
                          <a
                            v-if="event.source_url"
                            :href="event.source_url"
                            target="_blank"
                            rel="noopener noreferrer"
                            class="mt-1 inline-flex items-center gap-1 text-[8px] text-paper-faint/70 underline decoration-white/20 hover:text-paper"
                          >
                            来源：{{ event.source_title ?? "公开报道" }}
                          </a>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- career -->
                <section class="border-t border-white/[0.07] px-4 pb-8 pt-5 sm:px-6">
                  <div class="flex flex-wrap items-end justify-between gap-2 px-2">
                    <div>
                      <div class="label-eyebrow">CAREER TIMELINE</div>
                      <h3 class="mt-1 font-display text-[17px] tracking-wide text-paper">十八大以来履历轨迹</h3>
                    </div>
                    <div class="flex flex-wrap items-center gap-2.5">
                      <span v-for="item in legend" :key="item.key" class="flex items-center gap-1 text-[9px] text-paper-faint">
                        <span class="h-1.5 w-1.5 rounded-sm" :style="{ backgroundColor: categoryColor(item.key) }" />
                        {{ item.label }}
                      </span>
                      <span class="flex items-center gap-1 text-[9px] text-paper-faint">
                        <span class="h-1.5 w-1.5 rounded-sm border border-dashed border-white/50" />
                        代理（斜纹）
                      </span>
                    </div>
                  </div>

                  <div class="mt-3">
                    <div v-if="officer.loadingCareer" class="h-48 animate-pulse rounded-lg border border-white/[0.06] bg-white/[0.02]" />
                    <CareerGantt v-else-if="career" :career="career" />
                    <p v-else class="rounded-lg border border-dashed border-white/10 px-4 py-10 text-center text-[11px] text-paper-faint">
                      暂无 2012 年 11 月以来的履历记录
                    </p>
                  </div>

                  <div v-if="currentPositions.length" class="mt-6 px-2">
                    <div class="label-eyebrow">当前职务 / 省级职务可查看席位沿革</div>
                    <div class="mt-2 flex flex-wrap gap-1.5">
                      <template v-for="member in currentPositions" :key="member.tenure_id">
                        <button
                          v-if="member.region_code"
                          class="inline-flex items-center gap-1.5 rounded-md border border-white/10 bg-white/[0.03] px-2 py-1 text-[10px] text-paper-dim transition hover:border-vermilion/35 hover:text-paper"
                          @click="openSeat(member)"
                        >
                          <span class="h-1.5 w-1.5 rounded-full" :style="{ backgroundColor: categoryColor(member.category) }" />
                          {{ member.title }}
                          <span v-if="member.is_acting" class="text-vermilion-bright">代</span>
                          <AppIcon name="chevron-right" :size="9" class="text-paper-faint" />
                        </button>
                        <span
                          v-else
                          class="inline-flex cursor-default items-center gap-1.5 rounded-md border border-white/[0.07] bg-white/[0.02] px-2 py-1 text-[10px] text-paper-dim"
                          title="中央机构职务暂无地方席位沿革"
                        >
                          <span class="h-1.5 w-1.5 rounded-full" :style="{ backgroundColor: categoryColor(member.category) }" />
                          {{ member.title }}
                          <span class="text-[8px] text-paper-faint">中央</span>
                        </span>
                      </template>
                    </div>
                  </div>

                  <p class="mt-6 px-2 text-[9px] leading-relaxed text-paper-faint/70">
                    {{ career?.coverage.disclaimer }}
                  </p>
                </section>
              </template>
            </div>
          </aside>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>
