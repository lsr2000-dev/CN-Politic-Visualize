<script setup lang="ts">
import { computed } from "vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import CentralCommitteeBadge from "./CentralCommitteeBadge.vue";
import PartyRoleBadge from "./PartyRoleBadge.vue";
import { showCentralCommittee, visiblePartyRoles } from "@/utils/partyRoles";
import { useCentralStore } from "@/stores/central";
import { useOfficerStore } from "@/stores/app";
import { useTimelineStore } from "@/stores/timeline";

const central = useCentralStore();
const officer = useOfficerStore();
const timeline = useTimelineStore();

const institution = computed(() => central.selectedInstitution);
const detail = computed(() => central.selectedDetail);

function close(): void {
  central.selectInstitution(null, timeline.currentDate);
}

function openOfficer(id: number | null): void {
  if (id) void officer.openOfficer(id, timeline.currentDate);
}
</script>

<template>
  <Transition name="slide-panel">
    <aside v-if="institution" class="central-seat-drawer" aria-label="中央机构席位沿革">
      <header class="flex items-start justify-between gap-3 border-b border-white/10 px-5 py-4">
        <div class="min-w-0">
          <div class="label-eyebrow">CENTRAL SEAT / 机构席位沿革</div>
          <h2 class="mt-1 truncate font-display text-[20px] text-paper">{{ institution.name }}</h2>
          <div class="mt-1 text-[9px] text-paper-faint">
            {{ institution.institution_rank }} · {{ institution.institution_type }}
          </div>
        </div>
        <button class="btn-icon" title="关闭" @click="close"><AppIcon name="close" :size="14" /></button>
      </header>

      <div class="min-h-0 flex-1 overflow-y-auto px-5 py-4">
        <div v-if="!detail" class="py-10 text-center text-[11px] text-paper-faint">正在装载席位沿革…</div>
        <template v-else>
          <section>
            <div class="label-eyebrow mb-2">现任 / CURRENT</div>
            <div v-if="detail.leaders.length" class="space-y-2">
              <div v-for="leader in detail.leaders" :key="leader.name + leader.title" class="seat-person">
                <div class="flex flex-wrap items-center gap-1.5">
                  <button class="text-[12px] text-paper hover:text-vermilion-bright" @click="openOfficer(leader.officer_id)">
                    {{ leader.name }}
                  </button>
                  <span class="text-[10px] text-paper-faint">{{ leader.title }}</span>
                  <PartyRoleBadge :roles="visiblePartyRoles(leader.party_roles, institution.id)" />
                  <CentralCommitteeBadge
                    v-if="showCentralCommittee(leader.party_roles, institution.id)"
                    :committee="leader.central_committee"
                  />
                </div>
                <div v-if="leader.primary_post" class="mt-0.5 text-[9px] text-paper-faint">主要任职：{{ leader.primary_post }}</div>
                <div v-if="leader.central_committee?.status_note" class="mt-0.5 text-[9px] leading-snug text-paper-faint/80">
                  {{ leader.central_committee.status_note }}
                </div>
              </div>
            </div>
            <p v-else class="text-[10px] text-paper-faint">该机构当前正职待收录。</p>
          </section>

          <section class="mt-5 border-t border-white/10 pt-3">
            <div class="label-eyebrow mb-2">历任 / TENURES</div>
            <div class="space-y-2">
              <div
                v-for="leader in detail.history"
                :key="leader.name + leader.title + leader.start_date"
                class="seat-history-row"
              >
                <div class="flex flex-wrap items-center gap-1.5">
                  <button class="text-[11px] text-paper-dim hover:text-paper" @click="openOfficer(leader.officer_id)">
                    {{ leader.name }}
                  </button>
                  <span class="text-[9px] text-paper-faint">{{ leader.title }}</span>
                  <PartyRoleBadge :roles="visiblePartyRoles(leader.party_roles, institution.id)" compact />
                </div>
                <div class="mt-0.5 text-[9px] tabular-nums text-paper-faint">
                  {{ leader.start_date }} — {{ leader.end_date ?? "至今" }}
                </div>
              </div>
            </div>
          </section>

          <p class="mt-5 text-[9px] leading-relaxed text-paper-faint/70">
            点击姓名可打开官员档案。中央机构数据从 2022-10-16 起；中央委员/政治局身份按当前时点解析。
          </p>
        </template>
      </div>
    </aside>
  </Transition>
</template>

<style scoped>
.central-seat-drawer {
  position: fixed; right: 0; top: 64px; bottom: 0; z-index: 55;
  width: min(100vw, 520px);
  display: flex; flex-direction: column;
  border-left: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(9, 12, 17, 0.98);
  backdrop-filter: blur(20px);
  box-shadow: -24px 0 60px -30px rgba(0, 0, 0, 0.9);
}
.seat-person, .seat-history-row {
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 6px;
  padding: 7px 8px;
  background: rgba(255, 255, 255, 0.022);
}
@media (max-width: 640px) {
  .central-seat-drawer { top: 56px; width: 100vw; }
}
</style>
