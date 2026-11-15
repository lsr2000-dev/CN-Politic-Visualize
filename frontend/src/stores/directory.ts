import { computed, ref } from "vue";
import { defineStore } from "pinia";
import axios from "axios";
import { getDirectory } from "@/api/client";
import type { DirectoryResponse } from "@/types";

export const useDirectoryStore = defineStore("directory", () => {
  const query = ref("");
  const region = ref("");
  const category = ref("");
  const status = ref("");
  const rank = ref("");
  const page = ref(1);
  const pageSize = ref(50);
  const data = ref<DirectoryResponse | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  let controller: AbortController | null = null;

  const totalPages = computed(() =>
    data.value ? Math.max(1, Math.ceil(data.value.total / data.value.page_size)) : 1,
  );
  const hasFilters = computed(
    () => Boolean(query.value || region.value || category.value || status.value || rank.value),
  );

  async function load(): Promise<void> {
    controller?.abort();
    const current = new AbortController();
    controller = current;
    loading.value = true;
    error.value = null;
    try {
      data.value = await getDirectory(
        {
          q: query.value || undefined,
          region: region.value || undefined,
          category: category.value || undefined,
          status: status.value || undefined,
          rank: rank.value || undefined,
          page: page.value,
          page_size: pageSize.value,
        },
        current.signal,
      );
    } catch (caught) {
      if (axios.isCancel(caught)) return;
      error.value = caught instanceof Error ? caught.message : "名册加载失败";
    } finally {
      loading.value = false;
    }
  }

  function setPage(value: number): void {
    page.value = Math.min(Math.max(1, value), totalPages.value);
  }

  function resetFilters(): void {
    query.value = "";
    region.value = "";
    category.value = "";
    status.value = "";
    rank.value = "";
    page.value = 1;
  }

  return {
    query,
    region,
    category,
    status,
    rank,
    page,
    pageSize,
    data,
    loading,
    error,
    totalPages,
    hasFilters,
    load,
    setPage,
    resetFilters,
  };
});
