<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useDebounceFn } from "@vueuse/core";
import AppIcon from "./ui/AppIcon.vue";
import CentralCommitteeBadge from "./central/CentralCommitteeBadge.vue";
import PartyRoleBadge from "./central/PartyRoleBadge.vue";
import { showCentralCommittee, visiblePartyRoles, partyRankLevel } from "@/utils/partyRoles";
import { useDirectoryStore } from "@/stores/directory";
import { useAppStore, useOfficerStore } from "@/stores/app";
import { useMapStore } from "@/stores/map";
import { useTimelineStore } from "@/stores/timeline";
import { categoryColor, formatDate, formatDuration } from "@/utils/format";
import type { DirectoryItem } from "@/types";

const directory = useDirectoryStore();
const app = useAppStore();
const map = useMapStore();
const timeline = useTimelineStore();
const officer = useOfficerStore();

const search = ref(directory.query);
const showCoverage = ref(false);

const coverage = computed(() => directory.data?.coverage ?? null);
const items = computed(() => directory.data?.items ?? []);
const total = computed(() => directory.data?.total ?? 0);

const rankOptions = computed(() => {
  const seen = new Set<string>();
  return Object.entries(app.vocabulary?.ranks ?? {}).filter(([code, label]) => {
    if (code === "unknown" || seen.has(label)) return false;
    seen.add(label);
    return true;
  });
});

function displayRank(item: DirectoryItem): string {
  const level = partyRankLevel(item.party_roles);
  if (level === "national_leader") return app.vocabulary?.ranks.national_leader ?? "正国级";
  if (level === "vice_national_leader") return app.vocabulary?.ranks.vice_national_leader ?? "副国级";
  return item.rank_label;
}

const statusOptions = computed(() => Object.entries(app.vocabulary?.person_status ?? {}));

const categoryOptions = computed(() => app.meta?.categories ?? []);

const coveragePercent = computed(() =>
  coverage.value ? Math.round(coverage.value.principal_coverage * 1000) / 10 : 0,
);

const load = useDebounceFn(async () => {
  directory.query = search.value;
  directory.page = 1;
  await directory.load();
}, 240);

watch(search, () => {
  void load();
});

watch(
  () => [directory.region, directory.category, directory.status, directory.rank],
  () => {
    directory.page = 1;
    void directory.load();
  },
);

watch(
  () => directory.page,
  () => void directory.load(),
);

onMounted(() => {
  void directory.load();
});

function close(): void {
  app.closeDirectory();
}

function refresh(): void {
  void directory.load();
}

function pickRegion(code: string): void {
  directory.region = directory.region === code ? "" : code;
}

function openPerson(item: DirectoryItem): void {
  void officer.openOfficer(item.officer_id, timeline.currentDate);
}

function statusClass(status: string): string {
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

function period(item: DirectoryItem): string {
  if (!item.start_date) return "—";
  const estimated = item.start_precision === "snapshot";
  const start = estimated ? `约 ${formatDate(item.start_date, "YYYY.MM")}` : formatDate(item.start_date, "YYYY.MM");
  return `${start} — ${item.end_date ? formatDate(item.end_date, "YYYY.MM") : "至今"}`;
}

function duration(item: DirectoryItem): string {
  if (!item.start_date) return "—";
  const end = item.end_date
    ? new Date(item.end_date)
    : new Date(directory.data?.as_of ?? Date.now());
  const start = new Date(item.start_date);
  const days = Math.round((end.getTime() - start.getTime()) / 86400000) + 1;
  if (days <= 1 && item.start_precision === "snapshot") return "—";
  const text = formatDuration(Math.max(1, days));
  return item.start_precision === "snapshot" ? `约 ${text}` : text;
}

function exportCsv(): void {
  const rows = items.value.map((item) => [
    item.name,
    item.gender === "F" ? "女" : item.gender === "M" ? "男" : "",
    item.birth_year ?? "",
    item.native_place ?? "",
    item.current_title ?? "",
    item.region_name ?? "",
    item.rank_label,
    item.status_label,
    item.start_date ?? "",
    item.end_date ?? "至今",
    item.previous_title ?? "",
    item.next_title ?? item.status_label,
    item.updated_at,
  ]);
  const header = ["姓名", "性别", "出生年", "籍贯", "当前/最后职务", "地区", "级别", "状态", "起始", "结束", "上任前", "离任后", "更新时间"];
  const csv = [header, ...rows]
    .map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(","))
    .join("\n");
  const blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `polvis-directory-${directory.data?.as_of ?? "latest"}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);
}

function categoryName(key: string): string {
  return ({ party: "党委", congress: "人大", government: "政府", cppcc: "政协" } as Record<string, string>)[key] ?? key;
}

function provinceOptions(): Array<{ code: string; name: string }> {
  return map.regions
    .map((region) => ({ code: region.region_code, name: region.short_name }))
    .sort((a, b) => a.name.localeCompare(b.name, "zh"));
}
</script>

<template>
  <div class="fixed inset-x-0 bottom-0 top-16 z-30 flex flex-col bg-ink-950/[0.98] backdrop-blur-xl">
    <header class="flex shrink-0 flex-wrap items-end justify-between gap-3 border-b border-white/[0.08] px-4 py-3 sm:px-6">
      <div>
        <div class="flex items-center gap-2">
          <span class="h-3 w-[2px] bg-vermilion" />
          <span class="label-eyebrow">OFFICIAL DIRECTORY / 官员名册</span>
        </div>
        <h1 class="mt-1 font-display text-[22px] tracking-wide text-paper sm:text-[26px]">全国官员名册</h1>
        <p class="mt-1 text-[10px] text-paper-faint">
          与数据库同源 · {{ directory.data?.dataset_version ?? "—" }} · 截至
          {{ formatDate(directory.data?.as_of, "YYYY.MM.DD") }}
          <span class="mx-1.5 text-white/15">|</span>
          同步于 {{ formatDate(directory.data?.updated_at, "YYYY.MM.DD HH:mm") }}
        </p>
      </div>
      <div class="flex items-center gap-2">
        <button class="btn-ghost" @click="showCoverage = !showCoverage">
          <AppIcon name="layers" :size="12" />
          {{ showCoverage ? "收起覆盖看板" : "覆盖看板" }}
        </button>
        <button class="btn-ghost" @click="refresh">
          <AppIcon name="refresh" :size="12" :class="directory.loading ? 'animate-spin' : ''" />
          刷新
        </button>
        <button class="btn-ghost" @click="exportCsv">
          <AppIcon name="arrow-up-right" :size="12" />
          导出本页 CSV
        </button>
        <button class="btn-icon" aria-label="关闭名册" @click="close">
          <AppIcon name="close" :size="16" />
        </button>
      </div>
    </header>

    <div class="min-h-0 flex-1 overflow-y-auto px-4 py-4 sm:px-6">
      <!-- coverage summary -->
      <div class="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <div class="rounded-lg border border-white/[0.08] bg-white/[0.025] px-3 py-2.5">
          <div class="label-eyebrow">四套班子正职覆盖</div>
          <div class="mt-1 font-display text-xl text-paper tabular-nums">
            {{ coverage?.provinces_complete ?? "—" }}<span class="text-[11px] text-paper-faint">/{{ coverage?.provinces_total ?? 31 }}</span>
          </div>
          <div class="mt-1 text-[9px] text-gold">{{ coveragePercent }}% 省级单位 4/4</div>
        </div>
        <div class="rounded-lg border border-white/[0.08] bg-white/[0.025] px-3 py-2.5">
          <div class="label-eyebrow">任职记录</div>
          <div class="mt-1 font-display text-xl text-paper tabular-nums">{{ coverage?.tenures ?? "—" }}</div>
          <div class="mt-1 text-[9px] text-paper-faint">{{ coverage?.officers ?? 0 }} 名官员 · {{ coverage?.events ?? 0 }} 个状态事件</div>
        </div>
        <div class="rounded-lg border border-white/[0.08] bg-white/[0.025] px-3 py-2.5">
          <div class="label-eyebrow">名册快照</div>
          <div class="mt-1 font-display text-xl text-paper tabular-nums">{{ coverage?.roster_snapshots ?? "—" }}</div>
          <div class="mt-1 text-[9px] text-paper-faint">起始日待考的现任记录</div>
        </div>
        <div class="rounded-lg border border-white/[0.08] bg-white/[0.025] px-3 py-2.5">
          <div class="label-eyebrow">人工复核</div>
          <div class="mt-1 font-display text-xl text-paper tabular-nums">
            {{ coverage ? Math.round(coverage.verified_ratio * 100) : "—" }}<span class="text-[11px] text-paper-faint">%</span>
          </div>
          <div class="mt-1 text-[9px] text-vermilion-bright">演示数据，上线前须逐条复核</div>
        </div>
      </div>

      <!-- coverage matrix -->
      <Transition name="fade">
        <section v-if="showCoverage && coverage" class="mt-3 rounded-xl border border-white/[0.08] bg-white/[0.015] p-3">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <div class="label-eyebrow">省级覆盖矩阵 / 4 个正职席位</div>
            <div class="flex items-center gap-2 text-[9px] text-paper-faint">
              <span class="flex items-center gap-1"><span class="h-1.5 w-1.5 rounded-full" :style="{ backgroundColor: categoryColor('party') }" />党委</span>
              <span class="flex items-center gap-1"><span class="h-1.5 w-1.5 rounded-full" :style="{ backgroundColor: categoryColor('congress') }" />人大</span>
              <span class="flex items-center gap-1"><span class="h-1.5 w-1.5 rounded-full" :style="{ backgroundColor: categoryColor('government') }" />政府</span>
              <span class="flex items-center gap-1"><span class="h-1.5 w-1.5 rounded-full" :style="{ backgroundColor: categoryColor('cppcc') }" />政协</span>
            </div>
          </div>
          <div class="mt-3 flex flex-wrap gap-2">
            <div
              v-for="point in coverage.checkpoints"
              :key="point.date"
              class="rounded-md border border-white/[0.07] bg-white/[0.02] px-2.5 py-1.5"
            >
              <span class="text-[9px] tabular-nums text-paper-faint">{{ formatDate(point.date, "YYYY.MM") }}</span>
              <span class="ml-2 text-[11px] tabular-nums" :class="point.provinces_complete >= 20 ? 'text-jade' : 'text-gold'">
                {{ point.provinces_complete }}/{{ coverage.provinces_total }}
              </span>
            </div>
            <div class="rounded-md border border-gold/25 bg-gold/[0.06] px-2.5 py-1.5">
              <span class="text-[9px] tabular-nums text-gold">
                {{ coverage.vacancies.length }} 席确认空缺 · {{ coverage.provinces_accounted }}/{{ coverage.provinces_total }} 已说明
              </span>
            </div>
          </div>
          <div v-if="coverage.vacancies.length" class="mt-2 flex flex-wrap gap-1">
            <span
              v-for="vacancy in coverage.vacancies"
              :key="`${vacancy.region_code}-${vacancy.category}`"
              class="rounded border border-white/[0.07] px-1.5 py-0.5 text-[8px] text-paper-faint"
              :title="vacancy.reason"
            >
              {{ vacancy.region_name }} · {{ categoryName(vacancy.category) }}：{{ vacancy.reason }}
            </span>
          </div>
          <div class="mt-3 grid grid-cols-2 gap-1.5 sm:grid-cols-3 lg:grid-cols-5 xl:grid-cols-6">
            <button
              v-for="region in coverage.regions"
              :key="region.region_code"
              class="flex items-center gap-2 rounded-md border px-2 py-1.5 text-left transition"
              :class="directory.region === region.region_code
                ? 'border-vermilion/40 bg-vermilion/[0.07]'
                : 'border-white/[0.06] bg-white/[0.02] hover:border-white/20'"
              @click="pickRegion(region.region_code)"
            >
              <span class="min-w-0 flex-1 truncate text-[10px] text-paper-dim">{{ region.short_name }}</span>
              <span class="flex items-center gap-0.5">
                <span
                  v-for="key in ['party', 'congress', 'government', 'cppcc']"
                  :key="key"
                  class="h-1.5 w-1.5 rounded-full"
                  :style="{ backgroundColor: region.categories[key] ? categoryColor(key) : 'rgba(255,255,255,.1)' }"
                  :title="`${categoryName(key)}${region.categories[key] ? '已收录' : '未收录'}`"
                />
              </span>
              <span class="w-6 text-right text-[9px] tabular-nums" :class="region.filled === 4 ? 'text-jade' : 'text-paper-faint'">
                {{ region.filled }}/4
              </span>
            </button>
          </div>
          <p class="mt-2 text-[9px] leading-relaxed text-paper-faint/70">
            覆盖率为「截至 {{ formatDate(coverage.as_of, "YYYY.MM.DD") }} 的四套班子正职」口径。灰色圆点表示该省该班子未收录，不等同于席位空缺；具体缺口以页面表格与来源为准。
          </p>
        </section>
      </Transition>

      <!-- filters -->
      <div class="mt-4 flex flex-wrap items-center gap-2">
        <label class="relative min-w-[200px] flex-1">
          <AppIcon name="search" :size="13" class="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-paper-faint" />
          <input
            v-model="search"
            class="h-8 w-full rounded-md border border-white/10 bg-white/[0.03] pl-8 pr-2 text-[11px] text-paper outline-none transition placeholder:text-paper-faint/60 focus:border-vermilion/40"
            placeholder="搜索姓名、籍贯"
            aria-label="搜索官员"
          />
        </label>
        <select v-model="directory.region" class="h-8 rounded-md border border-white/10 bg-ink-900 px-2 text-[11px] text-paper-dim outline-none">
          <option value="">全部省份</option>
          <option v-for="region in provinceOptions()" :key="region.code" :value="region.code">{{ region.name }}</option>
        </select>
        <select v-model="directory.category" class="h-8 rounded-md border border-white/10 bg-ink-900 px-2 text-[11px] text-paper-dim outline-none">
          <option value="">全部班子</option>
          <option v-for="item in categoryOptions" :key="item.key" :value="item.key">{{ item.label }}</option>
        </select>
        <select v-model="directory.status" class="h-8 rounded-md border border-white/10 bg-ink-900 px-2 text-[11px] text-paper-dim outline-none">
          <option value="">全部状态</option>
          <option v-for="item in statusOptions" :key="item[0]" :value="item[0]">{{ item[1] }}</option>
        </select>
        <select v-model="directory.rank" class="h-8 rounded-md border border-white/10 bg-ink-900 px-2 text-[11px] text-paper-dim outline-none">
          <option value="">全部级别</option>
          <option v-for="item in rankOptions" :key="item[0]" :value="item[0]">{{ item[1] }}</option>
        </select>
        <button v-if="directory.hasFilters" class="btn-ghost h-8" @click="directory.resetFilters()">
          清除筛选
        </button>
        <span class="ml-auto text-[10px] tabular-nums text-paper-faint">
          {{ total }} 人 · 第 {{ directory.page }}/{{ directory.totalPages }} 页
        </span>
      </div>

      <!-- table -->
      <div class="mt-3 overflow-x-auto rounded-xl border border-white/[0.08]">
        <table class="w-full min-w-[1180px] border-collapse text-left">
          <thead class="bg-ink-900 text-[9px] uppercase tracking-wider text-paper-faint">
            <tr>
              <th class="px-3 py-2.5 font-medium">姓名 / 出生</th>
              <th class="px-3 py-2.5 font-medium">籍贯</th>
              <th class="px-3 py-2.5 font-medium">当前 / 最后职务</th>
              <th class="px-3 py-2.5 font-medium">级别</th>
              <th class="px-3 py-2.5 font-medium">状态</th>
              <th class="px-3 py-2.5 font-medium">任职起止</th>
              <th class="px-3 py-2.5 font-medium">上任前</th>
              <th class="px-3 py-2.5 font-medium">离任后 / 去向</th>
              <th class="px-3 py-2.5 font-medium">来源</th>
              <th class="px-3 py-2.5 font-medium">更新</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-white/[0.05]">
            <tr
              v-for="item in items"
              :key="item.officer_id"
              class="cursor-pointer bg-ink-950/30 transition hover:bg-white/[0.04]"
              @click="openPerson(item)"
            >
              <td class="px-3 py-2.5">
                <div class="flex items-center gap-2">
                  <span class="flex h-7 w-7 shrink-0 items-center justify-center rounded border border-white/10 bg-white/[0.03] font-display text-[11px] text-paper-dim">
                    {{ item.name.slice(0, 1) }}
                  </span>
                  <div class="min-w-0">
                    <div class="truncate text-[12px] text-paper">{{ item.name }}</div>
                    <div class="text-[9px] tabular-nums text-paper-faint">
                      {{ item.birth_year ?? "出生待考" }}<template v-if="item.gender"> · {{ item.gender === "F" ? "女" : "男" }}</template>
                    </div>
                    <PartyRoleBadge :roles="visiblePartyRoles(item.party_roles)" compact />
                    <CentralCommitteeBadge
                      v-if="showCentralCommittee(item.party_roles) || !item.party_roles?.length"
                      :committee="item.central_committee"
                      compact
                      class="mt-1"
                    />
                  </div>
                </div>
              </td>
              <td class="px-3 py-2.5 text-[10px] text-paper-dim">{{ item.native_place ?? "待补充" }}</td>
              <td class="max-w-[210px] px-3 py-2.5">
                <div class="truncate text-[11px] text-paper-dim">{{ item.current_title ?? "—" }}</div>
                <div class="mt-0.5 truncate text-[9px] text-paper-faint">
                  {{ item.region_name ?? (item.category === "other" ? "中央机构" : "—") }}
                </div>
              </td>
              <td class="px-3 py-2.5 text-[10px] text-paper-dim">{{ displayRank(item) }}</td>
              <td class="px-3 py-2.5">
                <span class="inline-flex rounded-full border px-1.5 py-0.5 text-[9px]" :class="statusClass(item.status)">
                  {{ item.status_label }}
                </span>
                <div v-if="item.status_date" class="mt-0.5 text-[8px] tabular-nums text-paper-faint">
                  {{ formatDate(item.status_date, "YYYY.MM") }}
                </div>
              </td>
              <td class="px-3 py-2.5">
                <div class="text-[9px] tabular-nums text-paper-dim">{{ period(item) }}</div>
                <div class="mt-0.5 text-[8px] text-paper-faint">{{ duration(item) }}</div>
              </td>
              <td class="max-w-[150px] truncate px-3 py-2.5 text-[9px] text-paper-faint">{{ item.previous_title ?? "—" }}</td>
              <td class="max-w-[150px] px-3 py-2.5 text-[9px]">
                <span v-if="item.next_title" class="text-paper-dim">{{ item.next_title }}</span>
                <span v-else class="text-paper-faint">{{ item.status === "active" ? "现任" : item.status_label }}</span>
              </td>
              <td class="px-3 py-2.5 text-[9px] tabular-nums" :class="item.source_count ? 'text-jade' : 'text-paper-faint'">
                {{ item.source_count || "待补" }}
              </td>
              <td class="px-3 py-2.5 text-[9px] tabular-nums text-paper-faint">{{ formatDate(item.updated_at, "MM.DD") }}</td>
            </tr>
            <tr v-if="!items.length && !directory.loading">
              <td colspan="10" class="px-3 py-16 text-center text-[11px] text-paper-faint">
                {{ directory.error ?? "没有符合条件的官员" }}
              </td>
            </tr>
            <tr v-if="directory.loading && !items.length">
              <td colspan="10" class="px-3 py-16 text-center text-[10px] tracking-widest text-paper-faint">
                正在读取数据库…
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="mt-3 flex items-center justify-between">
        <span class="text-[9px] text-paper-faint/70">
          点击行打开个人档案；名册来自数据库实时查询，非静态导出。
        </span>
        <div class="flex items-center gap-1.5">
          <button class="btn-ghost h-7" :disabled="directory.page <= 1" @click="directory.setPage(directory.page - 1)">上一页</button>
          <span class="px-1 text-[10px] tabular-nums text-paper-dim">{{ directory.page }} / {{ directory.totalPages }}</span>
          <button class="btn-ghost h-7" :disabled="directory.page >= directory.totalPages" @click="directory.setPage(directory.page + 1)">下一页</button>
        </div>
      </div>
    </div>
  </div>
</template>
