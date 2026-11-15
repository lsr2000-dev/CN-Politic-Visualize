import type { MetricKey, RegionSnapshot } from "@/types";

const SCALE = ["#1b2833", "#2b4a54", "#4f6a5f", "#9a7945", "#c8563a"];
const FILLED = ["#1a222b", "#2f3f47", "#4d5b4d", "#8a7a52", "#b08a4a"];

export function metricValue(region: RegionSnapshot, metric: MetricKey): number {
  return region.metrics[metric] ?? 0;
}

export function metricDomain(
  regions: RegionSnapshot[],
  metric: MetricKey,
): { min: number; max: number } {
  if (!regions.length) return { min: 0, max: 1 };
  const values = regions.map((region) => metricValue(region, metric));
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (metric.endsWith("_days")) {
    return { min: Math.max(0, min), max: Math.max(max, min + 365) };
  }
  return { min, max: Math.max(max, min + 1) };
}

function lerpColor(a: string, b: string, t: number): string {
  const pa = parseInt(a.slice(1), 16);
  const pb = parseInt(b.slice(1), 16);
  const channels = [16, 8, 0].map((shift) => {
    const va = (pa >> shift) & 255;
    const vb = (pb >> shift) & 255;
    return Math.round(va + (vb - va) * t);
  });
  return `#${channels.map((c) => c.toString(16).padStart(2, "0")).join("")}`;
}

export function metricColor(
  value: number,
  metric: MetricKey,
  domain: { min: number; max: number },
  rank?: number,
): string {
  if (metric === "filled") {
    return FILLED[Math.min(FILLED.length - 1, Math.max(0, Math.round(value)))];
  }
  const span = Math.max(1, domain.max - domain.min);
  const t = rank ?? Math.min(1, Math.max(0, (value - domain.min) / span));
  const segments = SCALE.length - 1;
  const scaled = t * segments;
  const index = Math.min(segments - 1, Math.floor(scaled));
  return lerpColor(SCALE[index], SCALE[index + 1], scaled - index);
}

/**
 * Percentile ranks spread the palette across all 31 provinces. A linear
 * scale clusters most "3–5 years in office" tenures into the same red band,
 * which makes the map unreadable.
 */
export function metricRankMap(
  regions: RegionSnapshot[],
  metric: MetricKey,
): Map<string, number> {
  const sorted = [...regions].sort(
    (a, b) => metricValue(a, metric) - metricValue(b, metric),
  );
  const ranks = new Map<string, number>();
  const total = sorted.length;
  let index = 0;
  while (index < total) {
    let end = index;
    while (
      end + 1 < total &&
      metricValue(sorted[end + 1], metric) === metricValue(sorted[index], metric)
    ) {
      end += 1;
    }
    const rank = total <= 1 ? 0.5 : (index + end) / 2 / (total - 1);
    for (let cursor = index; cursor <= end; cursor += 1) {
      ranks.set(sorted[cursor].region_code, rank);
    }
    index = end + 1;
  }
  return ranks;
}

export function metricGradient(metric: MetricKey): string {
  if (metric === "filled") {
    return `linear-gradient(90deg, ${FILLED.join(", ")})`;
  }
  return `linear-gradient(90deg, ${SCALE.join(", ")})`;
}

export function metricLegendLabels(
  metric: MetricKey,
  domain: { min: number; max: number },
): [string, string] {
  if (metric === "filled") return ["0 类", "4 类"];
  if (metric.endsWith("_days")) return [`${domain.min} 天`, `${domain.max} 天`];
  return [`${domain.min} 人`, `${domain.max} 人`];
}

export function headerLabel(metric: MetricKey): string {
  switch (metric) {
    case "party_days":
      return "党委书记在任时长";
    case "governor_days":
      return "政府主官在任时长";
    case "party_count":
      return "十八大以来党委书记人数";
    case "governor_count":
      return "十八大以来政府主官人数";
    case "filled":
      return "班子收录完整度";
    default:
      return "";
  }
}
