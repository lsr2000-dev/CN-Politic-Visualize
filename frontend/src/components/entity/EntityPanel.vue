<script setup lang="ts">
import { computed } from "vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import { useDraggablePanel } from "@/composables/useDraggablePanel";
import type { ViewMode } from "@/types";

const props = withDefaults(
  defineProps<{
    visible: boolean;
    mode: ViewMode;
    title: string;
    eyebrow?: string;
    subtitle?: string;
    pinned?: boolean;
    width?: number;
  }>(),
  { eyebrow: "ENTITY / 机构详情", subtitle: "", pinned: false, width: 520 },
);

const emit = defineEmits<{
  (event: "close"): void;
  (event: "update:mode", mode: ViewMode): void;
  (event: "toggle-pin"): void;
}>();

const { position, dragging, startDrag } = useDraggablePanel({
  width: props.width,
  offsetY: 84,
  margin: 16,
});

const floatingStyle = computed(() =>
  props.mode === "floating"
    ? { left: `${position.value.x}px`, top: `${position.value.y}px`, width: `${props.width}px` }
    : undefined,
);

const panelClass = computed(() => {
  if (props.mode === "fullscreen") {
    return "fixed inset-0 z-[72] flex flex-col bg-ink-950/97 backdrop-blur-2xl";
  }
  if (props.mode === "floating") {
    return "fixed z-[72] flex max-h-[calc(100vh-10rem)] flex-col overflow-hidden rounded-xl border border-white/10 bg-ink-900/97 shadow-panel backdrop-blur-2xl max-lg:inset-x-0 max-lg:bottom-0 max-lg:top-auto max-lg:max-h-[82vh] max-lg:w-full max-lg:rounded-t-2xl";
  }
  return "fixed bottom-0 right-0 top-16 z-[72] flex w-[min(100vw,560px)] flex-col border-l border-white/10 bg-ink-900/97 shadow-panel backdrop-blur-2xl";
});
</script>

<template>
  <Teleport to="body">
    <Transition name="slide-panel">
      <aside v-if="visible" :class="panelClass" :style="floatingStyle" aria-label="实体详情">
        <header
          class="flex shrink-0 items-start justify-between gap-3 border-b border-white/10 px-5 py-4"
          :class="mode === 'floating' ? 'cursor-grab active:cursor-grabbing' : ''"
          @pointerdown="mode === 'floating' ? startDrag($event) : undefined"
        >
          <div class="min-w-0">
            <div class="label-eyebrow">{{ eyebrow }}</div>
            <h2 class="mt-1 truncate font-display text-[22px] leading-tight text-paper">{{ title }}</h2>
            <p v-if="subtitle" class="mt-1 text-[9px] text-paper-faint">{{ subtitle }}</p>
          </div>

          <div class="flex shrink-0 items-center gap-1" data-no-drag @pointerdown.stop>
            <button
              class="btn-icon"
              :class="{ 'border-vermilion/40 bg-vermilion/10 text-vermilion-bright': pinned }"
              :title="pinned ? '取消固定' : '固定到对比栏'"
              @click="emit('toggle-pin')"
            >
              <AppIcon name="pin" :size="13" />
            </button>
            <button
              class="btn-icon hidden lg:inline-flex"
              :class="{ 'border-gold/35 text-gold': mode === 'sidebar' }"
              title="侧边栏"
              @click="emit('update:mode', 'sidebar')"
            >
              <AppIcon name="panel" :size="13" />
            </button>
            <button
              class="btn-icon hidden lg:inline-flex"
              :class="{ 'border-gold/35 text-gold': mode === 'floating' }"
              title="浮窗"
              @click="emit('update:mode', 'floating')"
            >
              <AppIcon name="float" :size="13" />
            </button>
            <button
              class="btn-icon"
              :class="{ 'border-gold/35 text-gold': mode === 'fullscreen' }"
              title="全屏"
              @click="emit('update:mode', mode === 'fullscreen' ? 'sidebar' : 'fullscreen')"
            >
              <AppIcon name="maximize" :size="13" />
            </button>
            <button class="btn-icon" title="关闭" @click="emit('close')">
              <AppIcon name="close" :size="13" />
            </button>
          </div>
        </header>

        <div v-if="mode === 'floating'" class="flex shrink-0 items-center gap-2 border-b border-white/[0.06] px-4 py-1.5 text-[8px] tracking-[0.2em] text-paper-faint/70" data-no-drag>
          <span class="h-1 w-1 rounded-full bg-paper-faint/60" /> FLOATING · 拖动标题移动
          <span class="ml-auto">{{ dragging ? "移动中" : "" }}</span>
        </div>

        <div
          class="min-h-0 flex-1 overflow-y-auto overscroll-contain"
          :class="mode === 'fullscreen' ? 'mx-auto w-full max-w-[1400px] px-8 py-6' : 'px-5 py-4'"
        >
          <slot />
        </div>
      </aside>
    </Transition>
  </Teleport>
</template>
