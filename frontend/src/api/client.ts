import axios, { AxiosError, type AxiosRequestConfig } from "axios";
import type {
  CareerResponse,
  CompareResponse,
  CoverageResponse,
  DirectoryResponse,
  MetaResponse,
  Officer,
  OfficerProfileResponse,
  RegionDetailResponse,
  RegionTimelineResponse,
  SeatHistoryResponse,
  SnapshotResponse,
  Vocabulary,
} from "@/types";

export const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";

const http = axios.create({
  baseURL: API_BASE,
  timeout: 20000,
  headers: { Accept: "application/json" },
});

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(message: string, status = 0, code = "network_error") {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

function normalizeError(error: unknown): never {
  if (axios.isCancel(error)) {
    throw error;
  }
  const axiosError = error as AxiosError<{ error?: { code?: string; message?: string }; detail?: unknown }>;
  const status = axiosError.response?.status ?? 0;
  const payload = axiosError.response?.data;
  let message = "数据服务暂时不可用";
  if (payload && typeof payload === "object" && "error" in payload && payload.error?.message) {
    message = payload.error.message;
  } else if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = payload.detail;
    if (typeof detail === "string") message = detail;
    else if (detail && typeof detail === "object" && "message" in detail) {
      message = String((detail as { message: unknown }).message);
    }
  } else if (axiosError.code === "ECONNABORTED") {
    message = "请求超时，请检查数据服务";
  }
  throw new ApiError(message, status, payload && typeof payload === "object" && "error" in payload
    ? payload.error?.code ?? "api_error"
    : "api_error");
}

/** Small ETag-aware cache: 31-province snapshots are ~120 KB, worth keeping. */
const snapshotCache = new Map<string, { data: SnapshotResponse; etag?: string }>();
const MAX_CACHED_SNAPSHOTS = 48;

export async function getSnapshot(
  date: string,
  options: { signal?: AbortSignal; force?: boolean } = {},
): Promise<SnapshotResponse> {
  const cached = snapshotCache.get(date);
  const config: AxiosRequestConfig = {
    params: { date },
    signal: options.signal,
    validateStatus: (status) => status === 200 || status === 304,
  };
  if (cached?.etag && !options.force) {
    config.headers = { "If-None-Match": cached.etag };
  }
  try {
    const response = await http.get<SnapshotResponse>("/map/snapshot", config);
    if (response.status === 304 && cached) {
      return cached.data;
    }
    const etag = response.headers.etag as string | undefined;
    snapshotCache.set(date, { data: response.data, etag });
    if (snapshotCache.size > MAX_CACHED_SNAPSHOTS) {
      const oldest = snapshotCache.keys().next().value;
      if (oldest) snapshotCache.delete(oldest);
    }
    return response.data;
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function getVocabulary(signal?: AbortSignal): Promise<Vocabulary> {
  try {
    const { data } = await http.get<Vocabulary>("/meta/vocabulary", { signal });
    return data;
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function getMeta(signal?: AbortSignal): Promise<MetaResponse> {
  try {
    const { data } = await http.get<MetaResponse>("/meta", { signal });
    return data;
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function getRegionDetail(
  code: string,
  date: string,
  signal?: AbortSignal,
): Promise<RegionDetailResponse> {
  try {
    const { data } = await http.get<RegionDetailResponse>(`/regions/${code}/leaders`, {
      params: { date },
      signal,
    });
    return data;
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function getRegionTimeline(
  code: string,
  signal?: AbortSignal,
): Promise<RegionTimelineResponse> {
  try {
    const { data } = await http.get<RegionTimelineResponse>(`/regions/${code}/timeline`, { signal });
    return data;
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function getSeatHistory(
  code: string,
  seatKey: string,
  date: string,
  signal?: AbortSignal,
): Promise<SeatHistoryResponse> {
  try {
    const { data } = await http.get<SeatHistoryResponse>(
      `/regions/${code}/seats/${seatKey}/history`,
      { params: { date }, signal },
    );
    return data;
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function getOfficer(
  id: number,
  date: string,
  signal?: AbortSignal,
): Promise<OfficerProfileResponse> {
  try {
    const { data } = await http.get<OfficerProfileResponse>(`/officers/${id}`, {
      params: { date },
      signal,
    });
    return data;
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function getCareer(
  id: number,
  range: { from?: string; to?: string } = {},
  signal?: AbortSignal,
): Promise<CareerResponse> {
  try {
    const { data } = await http.get<CareerResponse>(`/officers/${id}/career`, {
      params: { from: range.from, to: range.to },
      signal,
    });
    return data;
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function searchOfficers(q: string, signal?: AbortSignal): Promise<Officer[]> {
  try {
    const { data } = await http.get<Officer[]>("/officers", {
      params: { q, limit: 12 },
      signal,
    });
    return data;
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function getCompare(
  regions: string[],
  date: string,
  signal?: AbortSignal,
): Promise<CompareResponse> {
  try {
    const { data } = await http.get<CompareResponse>("/compare", {
      params: { regions: regions.join(","), date },
      signal,
    });
    return data;
  } catch (error) {
    throw normalizeError(error);
  }
}

export interface DirectoryQuery {
  q?: string;
  region?: string;
  category?: string;
  status?: string;
  rank?: string;
  date?: string;
  page?: number;
  page_size?: number;
}

export async function getDirectory(
  query: DirectoryQuery,
  signal?: AbortSignal,
): Promise<DirectoryResponse> {
  try {
    const { data } = await http.get<DirectoryResponse>("/directory", {
      params: query,
      signal,
    });
    return data;
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function getCoverage(
  date?: string,
  signal?: AbortSignal,
): Promise<CoverageResponse> {
  try {
    const { data } = await http.get<CoverageResponse>("/coverage", {
      params: { date },
      signal,
    });
    return data;
  } catch (error) {
    throw normalizeError(error);
  }
}

export function recentSnapshotDates(): string[] {
  return [...snapshotCache.keys()];
}

export function clearSnapshotCache(): void {
  snapshotCache.clear();
}

export async function getCentralOverview(
  date: string,
  signal?: AbortSignal,
): Promise<import("@/types").CentralOverview> {
  try {
    const { data } = await http.get<import("@/types").CentralOverview>("/central/overview", {
      params: { date }, signal,
    });
    return data;
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function getCentralOrg(
  team: string,
  date: string,
  signal?: AbortSignal,
): Promise<import("@/types").CentralOrgResponse> {
  try {
    const { data } = await http.get<import("@/types").CentralOrgResponse>("/central/org", {
      params: { team, date }, signal,
    });
    return data;
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function getCentralCommittee(
  name: string,
  date: string,
  signal?: AbortSignal,
): Promise<import("@/types").CentralCommitteeResponse> {
  try {
    const { data } = await http.get<import("@/types").CentralCommitteeResponse>("/central/committee", {
      params: { name, date }, signal,
    });
    return data;
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function getCentralInstitution(
  id: string,
  date: string,
  signal?: AbortSignal,
): Promise<import("@/types").CentralInstitutionDetail> {
  try {
    const { data } = await http.get<import("@/types").CentralInstitutionDetail>(
      `/institutions/central/${encodeURIComponent(id)}`,
      { params: { date }, signal },
    );
    return data;
  } catch (error) {
    throw normalizeError(error);
  }
}
