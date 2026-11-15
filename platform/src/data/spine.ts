import type { CompareOutput, SpineNode } from "./types";

export const productName = "Climate Sentinel";
export const productThesis =
  "Turn NISAR radar land-change trend into cost of inaction, recommended action, and regeneration with carbon credits.";

export const evidenceSpine: SpineNode[] = [
  {
    id: "nisar",
    label: "Surface trend (NISAR)",
    detail:
      "Cover and soil roughness change detected by radar — cloud-independent, useful in the semi-arid.",
  },
  {
    id: "index",
    label: "Desertification index",
    detail:
      "Combines surface trend with water stress and land use into an index comparable across municipalities.",
  },
  {
    id: "forecast",
    label: "Flora and fauna at 5 / 10 / 20 years",
    detail:
      "Projection of habitat loss, fragmentation, and species under pressure over planning horizons.",
  },
  {
    id: "cost",
    label: "Cost of inaction",
    detail:
      "Translates the trajectory into BRL of expected average loss (production, assistance, recovery) if nothing is done.",
  },
  {
    id: "action",
    label: "Recommended action",
    detail:
      "Prioritized measure package with order-of-magnitude cost to prevent versus inaction.",
  },
];

export const compareOutputs: CompareOutput[] = [
  {
    personaId: "gestor",
    framing: "Budget brief: PPA / amendment with BRL risk × BRL prevent",
    exportLabel: "PDF + methodology CSV",
  },
  {
    personaId: "prefeito",
    framing: "Term decision: local trend + policy template",
    exportLabel: "Municipality sheet + memo template",
  },
  {
    personaId: "assessor",
    framing: "Amendment attachment: auditable one-pager same day",
    exportLabel: "One-pager PDF + slides",
  },
  {
    personaId: "jornalista",
    framing: "Evidence story: findings, limits, and credits",
    exportLabel: "Publication kit + stable link",
  },
];