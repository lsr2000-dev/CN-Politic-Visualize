<script setup lang="ts">
import AppIcon from "./ui/AppIcon.vue";
import { useAppStore } from "@/stores/app";

const app = useAppStore();
const shortcuts = [
  ["← / →", "前后 1 天"],
  ["Shift + ← / →", "前后 1 个月"],
  ["Space", "播放 / 暂停"],
  ["/", "检索官员"],
  ["Esc", "关闭面板 / 抽屉"],
  ["Home / End", "跳到时间轴两端"],
];
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="app.helpOpen"
        class="fixed inset-0 z-[80] flex items-center justify-center bg-ink-950/70 px-4 backdrop-blur-sm"
        @click.self="app.helpOpen = false"
      >
        <div class="w-full max-w-[520px] overflow-hidden rounded-xl border border-white/10 bg-ink-900/95 shadow-panel">
          <div class="flex items-center justify-between border-b border-white/[0.08] px-5 py-3.5">
            <div class="flex items-center gap-2">
              <span class="h-3 w-[2px] bg-vermilion" />
              <h2 class="font-display text-[15px] tracking-wide text-paper">系统说明</h2>
            </div>
            <button class="btn-icon h-7 w-7" aria-label="关闭" @click="app.helpOpen = false">
              <AppIcon name="close" :size="14" />
            </button>
          </div>

          <div class="max-h-[65vh] overflow-y-auto px-5 py-4">
            <p class="text-[11px] leading-relaxed text-paper-dim">
              本系统在时间轴与中国地图上进行双重检索，呈现 2012 年 11 月党的十八大以来
              31 个省级行政区四套班子主官的任职切片，并支持官员跨省、跨部门履历穿透。
            </p>

            <div class="mt-4 grid grid-cols-2 gap-2">
              <div class="rounded-lg border border-white/[0.07] bg-white/[0.02] p-3">
                <div class="label-eyebrow">时间范围</div>
                <div class="mt-1 text-[11px] text-paper-dim">2012.11.08 — 今天</div>
              </div>
              <div class="rounded-lg border border-white/[0.07] bg-white/[0.02] p-3">
                <div class="label-eyebrow">空间范围</div>
                <div class="mt-1 text-[11px] text-paper-dim">31 省级行政区（地市接口预留）</div>
              </div>
            </div>

            <div class="mt-4">
              <div class="label-eyebrow">快捷键</div>
              <div class="mt-2 overflow-hidden rounded-lg border border-white/[0.07]">
                <div
                  v-for="(item, index) in shortcuts"
                  :key="item[0]"
                  class="flex items-center justify-between px-3 py-2 text-[11px]"
                  :class="index % 2 ? 'bg-white/[0.015]' : ''"
                >
                  <span class="text-paper-dim">{{ item[1] }}</span>
                  <kbd class="rounded border border-white/10 bg-ink-800 px-1.5 py-0.5 font-mono text-[9px] text-paper-faint">
                    {{ item[0] }}
                  </kbd>
                </div>
              </div>
            </div>

            <div class="mt-4 rounded-lg border border-gold/20 bg-gold/[0.05] p-3">
              <div class="flex items-center gap-1.5 text-[10px] text-gold">
                <AppIcon name="info" :size="12" />
                数据说明
              </div>
              <p class="mt-1.5 text-[10px] leading-relaxed text-paper-faint">
                {{ app.meta?.dataset.disclaimer }}
              </p>
              <p class="mt-1.5 text-[10px] text-paper-faint/80">
                当前数据版本 {{ app.meta?.dataset.id }} · 覆盖至
                {{ app.meta?.dataset.coverage_end }} · 超过该日期将标注「待更新」。
              </p>
            </div>
          </div>

          <div class="border-t border-white/[0.06] px-5 py-2.5 text-[9px] text-paper-faint">
            Vue 3 · FastAPI · PostgreSQL/PostGIS · ECharts
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
