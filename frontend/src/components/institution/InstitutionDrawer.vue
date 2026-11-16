<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from "vue";

const props = withDefaults(
  defineProps<{
    open: boolean;
    label?: string;
  }>(),
  { label: "机构信息" },
);
const emit = defineEmits<{ (event: "close"): void }>();

const drawer = ref<HTMLElement | null>(null);
let previouslyFocused: HTMLElement | null = null;

function close(): void {
  emit("close");
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape") {
    event.preventDefault();
    close();
  }
}

watch(
  () => props.open,
  async (open) => {
    if (open) {
      previouslyFocused = document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
      window.addEventListener("keydown", onKeydown);
      await nextTick();
      drawer.value?.focus();
    } else {
      window.removeEventListener("keydown", onKeydown);
      previouslyFocused?.focus();
      previouslyFocused = null;
    }
  },
  { immediate: true },
);

onBeforeUnmount(() => window.removeEventListener("keydown", onKeydown));
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="open"
        class="institution-drawer-backdrop fixed inset-0 z-[53] bg-ink-950/60 backdrop-blur-[2px]"
        @click.self="close"
      >
        <Transition name="drawer" appear>
          <aside
            v-if="open"
            ref="drawer"
            class="institution-drawer absolute right-0 top-0 flex h-full w-[min(660px,100vw)] flex-col border-l border-white/10 bg-ink-900 shadow-panel outline-none"
            role="dialog"
            aria-modal="true"
            :aria-label="label"
            tabindex="-1"
          >
            <slot />
          </aside>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.institution-drawer {
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.015), transparent 28%),
    rgb(13 17 23);
}
@media (max-width: 640px) {
  .institution-drawer {
    width: 100vw;
  }
}
</style>
