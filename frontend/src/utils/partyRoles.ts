import type { CentralPartyRole } from "@/types";

const COMMITTEE_ORDER: Record<string, number> = {
  politburo_standing: 0,
  politburo_member: 1,
  secretariat_member: 2,
  discipline_secretary: 3,
  military_chair: 4,
  military_vice_chair: 5,
  military_member: 6,
};
const MILITARY_ROLES = new Set(["military_chair", "military_vice_chair", "military_member"]);

const COLLECTIVE_CONTEXT = new Set([
  "party:politburo_standing",
  "party:politburo",
  "party:secretariat",
  "party:central_committee",
]);

export function highestCommitteeRole(
  roles: CentralPartyRole[] | null | undefined,
): CentralPartyRole | null {
  const committee = (roles ?? []).filter(
    (r) => r.role !== "secretariat_member" && !MILITARY_ROLES.has(r.role),
  );
  if (!committee.length) return null;
  return [...committee].sort((a, b) => COMMITTEE_ORDER[a.role] - COMMITTEE_ORDER[b.role])[0];
}

/** 政治局委员为副国级，政治局常委为正国级。 */
export function partyRankLevel(
  roles: CentralPartyRole[] | null | undefined,
): "national_leader" | "vice_national_leader" | null {
  if ((roles ?? []).some((r) => r.role === "politburo_standing")) return "national_leader";
  if ((roles ?? []).some((r) => r.role === "military_chair")) return "national_leader";
  if ((roles ?? []).some((r) => r.role === "politburo_member")) return "vice_national_leader";
  if ((roles ?? []).some((r) => r.role === "secretariat_member")) return "vice_national_leader";
  if ((roles ?? []).some((r) => r.role === "discipline_secretary")) return "vice_national_leader";
  if ((roles ?? []).some((r) => MILITARY_ROLES.has(r.role))) return "vice_national_leader";
  return null;
}

/**
 * 只显示最高层级的中央委员会/政治局身份；书记处书记不在这条层级链中，
 * 因此始终作为独立身份保留（除非当前就在书记处节点内部）。
 */
export function visiblePartyRoles(
  roles: CentralPartyRole[] | null | undefined,
  contextId = "",
): CentralPartyRole[] {
  if (!roles?.length) return [];
  if (contextId === "party:central_committee") return [];

  const highest = highestCommitteeRole(roles);
  const result: CentralPartyRole[] = [];
  if (highest) result.push(highest);

  const secretariat = roles.find((r) => r.role === "secretariat_member");
  if (secretariat) result.push(secretariat);

  const discipline = roles.find((r) => r.role === "discipline_secretary");
  if (discipline) result.push(discipline);

  for (const role of roles) {
    if (MILITARY_ROLES.has(role.role) && !result.some((item) => item.role === role.role)) {
      result.push(role);
    }
  }

  if (contextId === "party:politburo_standing") {
    return result.filter((r) => r.role !== "politburo_standing");
  }
  if (contextId === "party:politburo") {
    return result.filter((r) => r.role !== "politburo_member");
  }
  if (contextId === "party:secretariat") {
    return result.filter((r) => r.role !== "secretariat_member");
  }
  return result;
}

/** 中央委员只在没有更高政治局身份、且不在集体节点内部时显示。 */
export function showCentralCommittee(
  roles: CentralPartyRole[] | null | undefined,
  contextId = "",
): boolean {
  if (COLLECTIVE_CONTEXT.has(contextId)) return false;
  return !(roles ?? []).some((r) =>
    ["politburo_standing", "politburo_member", "secretariat_member", "discipline_secretary"].includes(r.role),
  );
}
