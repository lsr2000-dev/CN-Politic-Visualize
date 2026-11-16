import { computed, ref, shallowRef } from "vue";
import { defineStore } from "pinia";
import axios from "axios";
import { getCareer, getMeta, getOfficer, getSeatHistory, getVocabulary } from "@/api/client";
import type {
  CareerResponse,
  CategoryKey,
  GeoJson,
  MetaResponse,
  OfficerProfileResponse,
  SeatHistoryResponse,
  Vocabulary,
} from "@/types";
import { useMapStore } from "./map";
import { useTimelineStore } from "./timeline";

export const useAppStore = defineStore("app", () => {
  const meta = ref<MetaResponse | null>(null);
  const vocabulary = ref<Vocabulary | null>(null);
  const geo = shallowRef<GeoJson | null>(null);
  const ready = ref(false);
  const booting = ref(false);
  const bootError = ref<string | null>(null);
  const searchOpen = ref(false);
  const helpOpen = ref(false);
  const directoryOpen = ref(false);

  async function loadGeo(): Promise<GeoJson> {
    const response = await fetch(`${import.meta.env.BASE_URL}geo/china-provinces.json`);
    if (!response.ok) throw new Error("地图边界数据加载失败");
    return (await response.json()) as GeoJson;
  }

  async function bootstrap(): Promise<void> {
    if (ready.value || booting.value) return;
    booting.value = true;
    bootError.value = null;
    try {
      const [metaResponse, vocabResponse, geoJson] = await Promise.all([
        getMeta(), getVocabulary(), loadGeo(),
      ]);
      meta.value = metaResponse;
      vocabulary.value = vocabResponse;
      geo.value = geoJson;
      const timeline = useTimelineStore();
      timeline.initialize(metaResponse);

      // Deep link: /?date=2017-10-25&region=310000&view=fullscreen
      const params = new URLSearchParams(window.location.search);
      const requestedDate = params.get("date");
      if (requestedDate && /^\d{4}-\d{2}-\d{2}$/.test(requestedDate)) {
        timeline.setDate(requestedDate);
      }

      const map = useMapStore();
      await map.loadSnapshot(timeline.currentDate);
      const requestedRegion = params.get("region");
      if (requestedRegion && map.regionByCode(requestedRegion)) {
        map.selectRegion(requestedRegion);
      } else if (!map.selectedRegionCode) {
        map.selectRegion("110000");
      }
      const requestedView = params.get("view");
      if (requestedView === "sidebar" || requestedView === "floating" || requestedView === "fullscreen") {
        map.setViewMode(requestedView);
      }
      ready.value = true;

      const officerParam = params.get("officer");
      if (officerParam && Number.isFinite(Number(officerParam))) {
        void useOfficerStore().openOfficer(Number(officerParam), timeline.currentDate);
      }
      if (params.get("compare") === "1") {
        map.openCompare();
      }
      if (params.get("directory") === "1") {
        directoryOpen.value = true;
      }
    } catch (caught) {
      bootError.value = caught instanceof Error ? caught.message : "初始化失败";
    } finally {
      booting.value = false;
    }
  }

  function openSearch(): void {
    searchOpen.value = true;
  }

  function closeSearch(): void {
    searchOpen.value = false;
  }

  function openDirectory(): void {
    directoryOpen.value = true;
  }

  function closeDirectory(): void {
    directoryOpen.value = false;
  }

  return {
    meta,
    vocabulary,
    geo,
    ready,
    booting,
    bootError,
    searchOpen,
    helpOpen,
    directoryOpen,
    bootstrap,
    openSearch,
    closeSearch,
    openDirectory,
    closeDirectory,
  };
});

interface SeatContext {
  regionCode: string;
  regionName: string;
  seatKey: string;
  title: string;
  category: CategoryKey;
}

export const useOfficerStore = defineStore("officer", () => {
  const activeOfficerId = ref<number | null>(null);
  const profile = ref<OfficerProfileResponse | null>(null);
  const career = ref<CareerResponse | null>(null);
  const loadingProfile = ref(false);
  const loadingCareer = ref(false);
  const error = ref<string | null>(null);

  const activeSeat = ref<SeatContext | null>(null);
  const seatHistory = ref<SeatHistoryResponse | null>(null);
  const loadingSeat = ref(false);
  const seatError = ref<string | null>(null);

  let profileAbort: AbortController | null = null;
  let careerAbort: AbortController | null = null;
  let seatAbort: AbortController | null = null;

  const overlay = computed<"officer" | "seat" | null>(() => {
    if (activeOfficerId.value !== null) return "officer";
    if (activeSeat.value) return "seat";
    return null;
  });

  async function openOfficer(id: number, date: string): Promise<void> {
    closeSeat();
    activeOfficerId.value = id;
    profile.value = null;
    career.value = null;
    error.value = null;
    loadingProfile.value = true;
    loadingCareer.value = true;

    profileAbort?.abort();
    careerAbort?.abort();
    const profileController = new AbortController();
    const careerController = new AbortController();
    profileAbort = profileController;
    careerAbort = careerController;

    const [profileResult, careerResult] = await Promise.allSettled([
      getOfficer(id, date, profileController.signal),
      getCareer(id, {}, careerController.signal),
    ]);

    if (activeOfficerId.value !== id) return;
    if (profileResult.status === "fulfilled") {
      profile.value = profileResult.value;
    } else if (!axios.isCancel(profileResult.reason)) {
      error.value = profileResult.reason instanceof Error ? profileResult.reason.message : "档案加载失败";
    }
    if (careerResult.status === "fulfilled") {
      career.value = careerResult.value;
    } else if (!axios.isCancel(careerResult.reason)) {
      error.value = error.value ?? (careerResult.reason instanceof Error
        ? careerResult.reason.message
        : "履历加载失败");
    }
    loadingProfile.value = false;
    loadingCareer.value = false;
  }

  async function refreshProfile(date: string): Promise<void> {
    if (activeOfficerId.value === null) return;
    profileAbort?.abort();
    const controller = new AbortController();
    profileAbort = controller;
    try {
      profile.value = await getOfficer(activeOfficerId.value, date, controller.signal);
    } catch (caught) {
      if (!axios.isCancel(caught)) {
        error.value = caught instanceof Error ? caught.message : "档案加载失败";
      }
    }
  }

  function closeOfficer(): void {
    profileAbort?.abort();
    careerAbort?.abort();
    activeOfficerId.value = null;
    profile.value = null;
    career.value = null;
    error.value = null;
    loadingProfile.value = false;
    loadingCareer.value = false;
  }

  async function openSeat(
    context: SeatContext,
    date: string,
  ): Promise<void> {
    closeOfficer();
    activeSeat.value = context;
    seatHistory.value = null;
    seatError.value = null;
    loadingSeat.value = true;
    seatAbort?.abort();
    const controller = new AbortController();
    seatAbort = controller;
    try {
      seatHistory.value = await getSeatHistory(
        context.regionCode,
        context.seatKey,
        date,
        controller.signal,
      );
    } catch (caught) {
      if (!axios.isCancel(caught)) {
        seatError.value = caught instanceof Error ? caught.message : "席位履历加载失败";
      }
    } finally {
      loadingSeat.value = false;
    }
  }

  function closeSeat(): void {
    seatAbort?.abort();
    activeSeat.value = null;
    seatHistory.value = null;
    seatError.value = null;
    loadingSeat.value = false;
  }

  function closeAll(): void {
    closeOfficer();
    closeSeat();
  }

  return {
    activeOfficerId,
    profile,
    career,
    loadingProfile,
    loadingCareer,
    error,
    activeSeat,
    seatHistory,
    loadingSeat,
    seatError,
    overlay,
    openOfficer,
    refreshProfile,
    closeOfficer,
    openSeat,
    closeSeat,
    closeAll,
  };
});
