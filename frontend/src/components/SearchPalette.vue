<script setup lang="ts">
import { nextTick, ref, watch } from "vue";
import { useDebounceFn } from "@vueuse/core";
import AppIcon from "./ui/AppIcon.vue";
import { useAppStore, useOfficerStore } from "@/stores/app";
import { useTimelineStore } from "@/stores/timeline";
import { searchOfficers } from "@/api/client";
import { initials } from "@/utils/format";
import type { Officer } from "@/types";

const app = useAppStore();
const officer = useOfficerStore();
const timeline = useTimelineStore();

const query = ref("");
const results = ref<Officer[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);
const activeIndex = ref(0);
const input = ref<HTMLInputElement | null>(null);

const suggestions = ["李强", "陈吉宁", "应勇", "马兴瑞", "蔡奇", "陈敏尔"];

let controller: AbortController | null = null;

const runSearch = useDebounceFn(async (value: string) => {
  controller?.abort();
  const current = new AbortController();
  controller = current;
  if (!value.trim()) {
    results.value = [];
    loading.value = false;
    return;
  }
  loading.value = true;
  error.value = null;
  try {
    const items = await searchOfficers(value.trim(), current.signal);
    results.value = items;
    activeIndex.value = 0;
  } catch (caught) {
    if ((caught as Error).name === "CanceledError") return;
    error.value = caught instanceof Error ? caught.message : "检索失败";
    results.value = [];
  } finally {
    loading.value = false;
  }
}, 220);

watch(query, (value) => {
  loading.value = Boolean(value.trim());
  void runSearch(value);
});

watch(
  () => app.searchOpen,
  async (open) => {
    if (!open) return;
    query.value = "";
    results.value = [];
    error.value = null;
    activeIndex.value = 0;
    await nextTick();
    input.value?.focus();
  },
);

function close(): void {
  app.closeSearch();
}

function choose(person: Officer): void {
  app.closeSearch();
  void officer.openOfficer(person.id, timeline.currentDate);
}

function move(delta: number): void {
  if (!results.value.length) return;
  activeIndex.value = (activeIndex.value + delta + results.value.length) % results.value.length;
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === "ArrowDown") {
    event.preventDefault();
    move(1);
  } else if (event.key === "ArrowUp") {
    event.preventDefault();
    move(-1);
  } else if (event.key === "Enter") {
    event.preventDefault();
    const person = results.value[activeIndex.value];
    if (person) choose(person);
  } else if (event.key === "Escape") {
    close();
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="app.searchOpen"
        class="fixed inset-0 z-[80] flex items-start justify-center bg-ink-950/70 px-4 pt-[12vh] backdrop-blur-sm"
        @click.self="close"
      >
        <div
          class="w-full max-w-[560px] overflow-hidden rounded-xl border border-white/10 bg-ink-900/95 shadow-panel"
          role="dialog"
          aria-label="检索官员"
        >
          <div class="flex items-center gap-2.5 border-b border-white/[0.08] px-4 py-3">
            <AppIcon name="search" :size="16" class="text-paper-faint" />
            <input
              ref="input"
              v-model="query"
              class="h-7 flex-1 bg-transparent text-[14px] text-paper outline-none placeholder:text-paper-faint/60"
              placeholder="输入姓名或籍贯，例如：李强"
              aria-label="搜索官员"
              @keydown="onKeydown"
            />
            <button class="rounded border border-white/10 px-1.5 py-0.5 text-[9px] text-paper-faint" @click="close">
              ESC
            </button>
          </div>

          <div class="max-h-[52vh] overflow-y-auto p-2">
            <div v-if="!query.trim()" class="px-2 py-3">
              <div class="label-eyebrow">试试检索 / SUGGESTIONS</div>
              <div class="mt-2 flex flex-wrap gap-1.5">
                <button
                  v-for="name in suggestions"
                  :key="name"
                  class="chip transition hover:border-vermilion/40 hover:text-paper"
                  @click="query = name"
                >
                  {{ name }}
                </button>
              </div>
              <p class="mt-4 text-[10px] leading-relaxed text-paper-faint">
                支持按姓名与籍贯模糊匹配。选中后打开个人档案与十八大以来跨省履历甘特图。
              </p>
            </div>

            <div v-else-if="loading" class="space-y-1 p-1">
              <div v-for="index in 3" :key="index" class="flex items-center gap-3 rounded-lg px-2 py-2.5">
                <div class="skeleton h-8 w-8 rounded-md" />
                <div class="flex-1 space-y-1.5">
                  <div class="skeleton h-3 w-20 rounded" />
                  <div class="skeleton h-2 w-32 rounded" />
                </div>
              </div>
            </div>

            <div v-else-if="error" class="px-3 py-6 text-center text-[11px] text-vermilion-bright">
              {{ error }}
            </div>

            <div v-else-if="!results.length" class="px-3 py-8 text-center">
              <p class="text-[12px] text-paper-dim">未找到「{{ query }}」</p>
              <p class="mt-1 text-[10px] text-paper-faint">试试只输入姓氏，或改用籍贯关键词</p>
            </div>

            <div v-else class="space-y-0.5">
              <button
                v-for="(person, index) in results"
                :key="person.id"
                class="flex w-full items-center gap-3 rounded-lg px-2.5 py-2 text-left transition"
                :class="index === activeIndex ? 'bg-vermilion/10' : 'hover:bg-white/[0.05]'"
                @mouseenter="activeIndex = index"
                @click="choose(person)"
              >
                <span
                  class="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-white/10 bg-white/[0.04] font-display text-[13px] text-paper-dim"
                >
                  {{ initials(person.name) }}
                </span>
                <span class="min-w-0 flex-1">
                  <span class="flex items-baseline gap-2">
                    <span class="text-[13px] text-paper">{{ person.name }}</span>
                    <span v-if="person.birth_year" class="text-[9px] tabular-nums text-paper-faint">
                      {{ person.birth_year }}
                    </span>
                  </span>
                  <span class="mt-0.5 block truncate text-[10px] text-paper-faint">
                    {{ person.native_place || "籍贯待补充" }}
                    <template v-if="person.education"> · {{ person.education }}</template>
                  </span>
                </span>
                <AppIcon name="arrow-up-right" :size="13" class="shrink-0 text-paper-faint" />
              </button>
            </div>
          </div>

          <div class="flex items-center justify-between border-t border-white/[0.06] px-4 py-2 text-[9px] text-paper-faint">
            <span>↑↓ 选择 · Enter 打开 · Esc 关闭</span>
            <span>{{ results.length ? `${results.length} 条结果` : "官员档案" }}</span>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
