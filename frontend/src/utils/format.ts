import dayjs from "dayjs";

export function formatDate(value: string | null | undefined, pattern = "YYYY.MM.DD"): string {
  if (!value) return "至今";
  return dayjs(value).format(pattern);
}

export function formatMonth(value: string | null | undefined): string {
  if (!value) return "至今";
  return dayjs(value).format("YYYY.MM");
}

export function formatDuration(days: number): string {
  if (!Number.isFinite(days) || days <= 0) return "不足 1 天";
  if (days < 45) return `${days} 天`;
  const years = Math.floor(days / 365);
  let months = Math.round((days - years * 365) / 30.44);
  if (months >= 12) {
    return `${years + 1} 年`;
  }
  if (years > 0) {
    return months > 0 ? `${years} 年 ${months} 个月` : `${years} 年`;
  }
  return `${Math.max(1, months)} 个月`;
}

export function ageOf(birthYear: number | null | undefined, at: string): number | null {
  if (!birthYear) return null;
  return dayjs(at).year() - birthYear;
}

export function pct(part: number, total: number): number {
  if (!total) return 0;
  return Math.min(100, Math.max(0, (part / total) * 100));
}

export function dateToDay(value: string): number {
  return dayjs(value).startOf("day").valueOf();
}

export function diffDays(a: string, b: string): number {
  return dayjs(b).startOf("day").diff(dayjs(a).startOf("day"), "day");
}

export function initials(name: string): string {
  if (!name) return "?";
  // 复姓 / 少数民族姓名取首字即可，视觉上更稳定
  return name.slice(0, 1);
}

export function categoryColor(key: string): string {
  switch (key) {
    case "party":
      return "#c8492f";
    case "congress":
      return "#4d7ea8";
    case "government":
      return "#b08a4a";
    case "cppcc":
      return "#5c8a76";
    default:
      return "#7b8794";
  }
}

export function hexToRgba(hex: string, alpha: number): string {
  const normalized = hex.replace("#", "");
  const value = parseInt(normalized, 16);
  const r = (value >> 16) & 255;
  const g = (value >> 8) & 255;
  const b = value & 255;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}
