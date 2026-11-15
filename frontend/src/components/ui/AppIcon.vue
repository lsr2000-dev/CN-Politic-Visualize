<script setup lang="ts">
type IconName =
  | "panel"
  | "float"
  | "maximize"
  | "pin"
  | "close"
  | "chevron-down"
  | "chevron-right"
  | "play"
  | "pause"
  | "search"
  | "clock"
  | "arrow-up-right"
  | "users"
  | "layers"
  | "refresh"
  | "calendar"
  | "map-pin"
  | "compare"
  | "info"
  | "arrow-left"
  | "minus"
  | "plus"
  | "check";

const props = withDefaults(
  defineProps<{ name: IconName; size?: number | string; strokeWidth?: number }>(),
  { size: 16, strokeWidth: 1.6 },
);

const paths: Record<IconName, string[]> = {
  panel: ["M3 4h18v16H3z", "M15 4v16"],
  float: ["M4 5h10v10H4z", "M10 9h10v10H10z"],
  maximize: ["M8 3H3v5", "M16 3h5v5", "M21 16v5h-5", "M3 16v5h5"],
  pin: ["M12 17v5", "M9 3h6l-1.2 6 3.2 3v2H7v-2l3-3z"],
  close: ["M6 6l12 12", "M18 6L6 18"],
  "chevron-down": ["M6 9l6 6 6-6"],
  "chevron-right": ["M9 6l6 6-6 6"],
  play: ["M8 5l11 7-11 7z"],
  pause: ["M8 5v14", "M16 5v14"],
  search: ["M11 19a8 8 0 100-16 8 8 0 000 16z", "M21 21l-4.3-4.3"],
  clock: ["M12 21a9 9 0 100-18 9 9 0 000 18z", "M12 7v5l3 2"],
  "arrow-up-right": ["M7 17L17 7", "M8 7h9v9"],
  users: [
    "M16 21v-2a4 4 0 00-4-4H6a4 4 0 00-4 4v2",
    "M9 11a4 4 0 100-8 4 4 0 000 8",
    "M22 21v-2a4 4 0 00-3-3.87",
    "M16 3.13a4 4 0 010 7.75",
  ],
  layers: ["M12 2l9 5-9 5-9-5z", "M3 12l9 5 9-5", "M3 17l9 5 9-5"],
  refresh: ["M21 12a9 9 0 11-3-6.7", "M21 3v6h-6"],
  calendar: ["M4 5h16v16H4z", "M8 3v4", "M16 3v4", "M4 10h16"],
  "map-pin": ["M12 22s7-6.2 7-12a7 7 0 10-14 0c0 5.8 7 12 7 12z", "M12 10a2 2 0 100-4 2 2 0 000 4"],
  compare: ["M4 4h6v16H4z", "M14 4h6v16h-6z"],
  info: ["M12 21a9 9 0 100-18 9 9 0 000 18z", "M12 11v5", "M12 8h.01"],
  "arrow-left": ["M19 12H5", "M12 19l-7-7 7-7"],
  minus: ["M5 12h14"],
  plus: ["M12 5v14", "M5 12h14"],
  check: ["M20 6L9 17l-5-5"],
};
</script>

<template>
  <svg
    :width="props.size"
    :height="props.size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    :stroke-width="props.strokeWidth"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path v-for="path in paths[props.name]" :key="path" :d="path" />
  </svg>
</template>
