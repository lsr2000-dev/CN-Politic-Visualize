import { computed, ref, watch } from "vue";
import { defineStore } from "pinia";
import { getCentralCommittee, getCentralInstitution, getCentralOrg, getCentralOverview } from "@/api/client";
import { useTimelineStore } from "./timeline";
import type {
  CentralCommittee,
  CentralInstitution,
  CentralInstitutionDetail,
  CentralOrgResponse,
  CentralOverview,
  CentralPartyRole,
} from "@/types";

export const useCentralStore = defineStore("central", () => {
  const timeline = useTimelineStore();
  const overview = ref<CentralOverview | null>(null);
  const org = ref<CentralOrgResponse | null>(null);
  const selectedTeam = ref<string | null>(null);
  const selectedInstitution = ref<CentralInstitution | null>(null);
  const selectedDetail = ref<CentralInstitutionDetail | null>(null);
  const loading = ref(false);
  const detailLoading = ref(false);
  const error = ref<string | null>(null);
  const committeeCache = ref<Record<string, CentralCommittee | null>>({});
  const partyRoleCache = ref<Record<string, CentralPartyRole[]>>({});
  const loadedDate = ref<string | null>(null);

  const isOpen = computed(() => Boolean(selectedTeam.value));

  async function loadOverview(date: string): Promise<void> {
    try {
      overview.value = await getCentralOverview(date);
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : "中央机构加载失败";
    }
  }

  async function openTeam(team: string, date: string): Promise<void> {
    selectedTeam.value = team;
    selectedInstitution.value = null;
    selectedDetail.value = null;
    loading.value = true;
    error.value = null;
    try {
      org.value = await getCentralOrg(team, date);
      loadedDate.value = date;
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : "组织架构加载失败";
    } finally {
      loading.value = false;
    }
  }

  async function refresh(date: string): Promise<void> {
    if (!selectedTeam.value) return;
    const currentId = selectedInstitution.value?.id ?? null;
    loading.value = true;
    error.value = null;
    try {
      const [nextOrg] = await Promise.all([
        getCentralOrg(selectedTeam.value, date),
        loadOverview(date),
      ]);
      org.value = nextOrg;
      loadedDate.value = date;
      if (currentId) {
        const next = nextOrg.institutions.find((item) => item.id === currentId) ?? null;
        if (next) {
          await selectInstitution(next, date);
        } else {
          selectedInstitution.value = null;
          selectedDetail.value = null;
        }
      }
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : "中央机构加载失败";
    } finally {
      loading.value = false;
    }
  }

  let refreshTimer: number | undefined;

  // Single reactive bridge: every central board follows the global timeline.
  watch(
    () => timeline.currentDate,
    (date) => {
      if (refreshTimer) window.clearTimeout(refreshTimer);
      refreshTimer = window.setTimeout(() => {
        refreshTimer = undefined;
        void refresh(date);
      }, 180);
    },
  );

  function close(): void {
    selectedTeam.value = null;
    selectedInstitution.value = null;
    selectedDetail.value = null;
    org.value = null;
  }

  async function selectInstitution(inst: CentralInstitution | null, date: string): Promise<void> {
    selectedInstitution.value = inst;
    selectedDetail.value = null;
    if (!inst) return;
    detailLoading.value = true;
    try {
      selectedDetail.value = await getCentralInstitution(inst.id, date);
    } catch {
      selectedDetail.value = null;
    } finally {
      detailLoading.value = false;
    }
  }

  async function loadCommittee(name: string, date: string): Promise<CentralCommittee | null> {
    const key = `${name}:${date}`;
    if (key in committeeCache.value) return committeeCache.value[key];
    try {
      const response = await getCentralCommittee(name, date);
      committeeCache.value[key] = response.committee;
      partyRoleCache.value[key] = response.party_roles ?? [];
      return response.committee;
    } catch {
      committeeCache.value[key] = null;
      return null;
    }
  }

  function committeeFor(name: string, date: string): CentralCommittee | null {
    return committeeCache.value[`${name}:${date}`] ?? null;
  }

  function partyRolesFor(name: string, date: string): CentralPartyRole[] {
    return partyRoleCache.value[`${name}:${date}`] ?? [];
  }

  return {
    overview,
    org,
    selectedTeam,
    selectedInstitution,
    selectedDetail,
    loading,
    detailLoading,
    error,
    loadedDate,
    isOpen,
    loadOverview,
    openTeam,
    refresh,
    close,
    selectInstitution,
    loadCommittee,
    committeeFor,
    partyRolesFor,
  };
});
