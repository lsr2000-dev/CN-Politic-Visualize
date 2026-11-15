import { onMounted, onScopeDispose, ref } from "vue";
import { clamp } from "@/utils/format";

interface Options {
  width: number;
  margin?: number;
  offsetY?: number;
}

/**
 * Pointer-drag for the floating panel. Position is clamped inside the
 * viewport on drag and on resize; disabled on small screens where the panel
 * becomes a bottom sheet.
 */
export function useDraggablePanel(options: Options) {
  const margin = options.margin ?? 16;
  const offsetY = options.offsetY ?? 80;
  const position = ref({ x: 0, y: offsetY });
  const dragging = ref(false);

  let offset = { x: 0, y: 0 };

  function maxX(): number {
    return Math.max(margin, window.innerWidth - options.width - margin);
  }

  function clampPosition(x: number, y: number) {
    return {
      x: clamp(x, margin, maxX()),
      y: clamp(y, offsetY, Math.max(offsetY, window.innerHeight - 180)),
    };
  }

  function reset(): void {
    position.value = clampPosition(window.innerWidth - options.width - 28, offsetY + 12);
  }

  function onPointerMove(event: PointerEvent): void {
    if (!dragging.value) return;
    position.value = clampPosition(event.clientX - offset.x, event.clientY - offset.y);
  }

  function endDrag(): void {
    dragging.value = false;
    window.removeEventListener("pointermove", onPointerMove);
    window.removeEventListener("pointerup", endDrag);
  }

  function startDrag(event: PointerEvent): void {
    if (window.innerWidth < 900) return;
    if ((event.target as HTMLElement).closest("[data-no-drag]")) return;
    const rect = (event.currentTarget as HTMLElement).getBoundingClientRect();
    offset = { x: event.clientX - rect.left, y: event.clientY - rect.top };
    dragging.value = true;
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", endDrag, { once: true });
  }

  function onResize(): void {
    position.value = clampPosition(position.value.x, position.value.y);
  }

  onMounted(() => {
    reset();
    window.addEventListener("resize", onResize);
  });

  onScopeDispose(() => {
    window.removeEventListener("resize", onResize);
    endDrag();
  });

  return { position, dragging, startDrag, reset };
}
