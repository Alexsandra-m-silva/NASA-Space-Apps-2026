import {
  IMPACT_LABELS,
  LEVEL_LABELS,
  RISK_ORDER,
  type GeoLevel,
  type ImpactType,
  type RiskLevel,
  type Territory,
} from "@/data/explore/types";

export type ActionKind = "preservar" | "retardar" | "reverter";

export type ActionSuggestion = {
  id: string;
  kind: ActionKind;
  title: string;
  summary: string;
  why: string;
  /** Higher = show first */
  priority: number;
  metrics: { label: string; value: string }[];
  relatedImpacts: ImpactType[];
};

export const ACTION_KIND_LABELS: Record<ActionKind, string> = {
  preservar: "Preserve",
  retardar: "Slow",
  reverter: "Reverse",
};

const ACTION_TEMPLATES: {
  id: string;
  kind: ActionKind;
  title: string;
  summary: string;
  impacts?: ImpactType[];
  /** Min risk weight to activate */
  minRiskWeight?: number;
  prefersRegen?: Territory["regeneracaoStatus"][];
}[] = [
  {
    id: "protecao-remanescentes",
    kind: "preservar",
    title: "Protect remnants and stable areas",
    summary:
      "Consolidate protection of native vegetation and still-stable soils before the trend advances.",
    prefersRegen: ["protegido", "regenerado", "em_regeneracao"],
  },
  {
    id: "gestao-hidrica",
    kind: "retardar",
    title: "Emergency water management",
    summary:
      "Prioritize cisterns, spring restoration, and efficient use to slow water deficit.",
    impacts: ["deficit_hidrico"],
    minRiskWeight: 2,
  },
  {
    id: "seguranca-alimentar",
    kind: "retardar",
    title: "Buffer food insecurity",
    summary:
      "Stockpiling, local procurement, and assistance to reduce harm while the trend has not reversed.",
    impacts: ["inseguranca_alimentar"],
    minRiskWeight: 2,
  },
  {
    id: "renda-safra",
    kind: "retardar",
    title: "Insurance and income diversification",
    summary:
      "Mitigate crop loss with guided rural credit, insurance, and drought-resilient crops.",
    impacts: ["perda_renda"],
  },
  {
    id: "corredores-biodiversidade",
    kind: "preservar",
    title: "Biodiversity corridors and buffers",
    summary:
      "Maintain habitat connectivity and slow pressure on fauna and flora at degradation edges.",
    impacts: ["pressao_biodiversidade"],
  },
  {
    id: "acolhida-migracao",
    kind: "retardar",
    title: "Relocation support and planning",
    summary:
      "Coordinate civil defense and municipal networks to reduce human harm while stabilizing the territory.",
    impacts: ["migracao"],
    minRiskWeight: 2,
  },
  {
    id: "regeneracao-ativa",
    kind: "reverter",
    title: "Active restoration of eligible areas",
    summary:
      "Restore priority hectares to reverse desertification and unlock carbon credit potential.",
    prefersRegen: ["a_recuperar", "em_regeneracao"],
    minRiskWeight: 2,
  },
  {
    id: "solos-revegetacao",
    kind: "reverter",
    title: "Soil recovery and revegetation",
    summary:
      "Intervene where the trend rises fastest: ground cover, native species, and erosion control.",
    minRiskWeight: 3,
  },
];

function formatBRL(mi: number): string {
  if (!Number.isFinite(mi)) return "—";
  if (mi >= 1000) return `R$ ${(mi / 1000).toFixed(1)} bn`;
  return `R$ ${Math.round(mi)} M`;
}

function formatHa(ha: number): string {
  if (ha >= 1_000_000) return `${(ha / 1_000_000).toFixed(1)} M ha`;
  if (ha >= 1000) return `${Math.round(ha / 1000)}k ha`;
  return `${Math.round(ha)} ha`;
}

function formatCredits(t: number): string {
  if (t >= 1_000_000) return `${(t / 1_000_000).toFixed(1)} M tCO₂e`;
  if (t >= 1000) return `${Math.round(t / 1000)}k tCO₂e`;
  return `${Math.round(t)} tCO₂e`;
}

export function buildActionSuggestions(input: {
  items: Territory[];
  level: GeoLevel;
  impact: ImpactType | "todos";
  risk: RiskLevel | "todos";
}): ActionSuggestion[] {
  const { items, level, impact } = input;
  if (items.length === 0) return [];

  const levelLabel = LEVEL_LABELS[level].toLowerCase();
  const impactCount = new Map<ImpactType, number>();
  let riskWeight = 0;
  let naoAgir = 0;
  let prevenir = 0;
  let areaHa = 0;
  let creditos = 0;
  let maxTrend = 0;
  const regenCount = {
    a_recuperar: 0,
    em_regeneracao: 0,
    regenerado: 0,
    protegido: 0,
  };

  for (const t of items) {
    riskWeight += RISK_ORDER[t.risk];
    naoAgir += t.custoNaoAgirMi;
    prevenir += t.custoPrevenirMi;
    areaHa += t.areaRecuperavelHa;
    creditos += t.creditosCarbonoTco2e;
    maxTrend = Math.max(maxTrend, t.tendenciaPp);
    regenCount[t.regeneracaoStatus] += 1;
    for (const imp of t.impacts) {
      impactCount.set(imp, (impactCount.get(imp) ?? 0) + 1);
    }
  }

  const avgRisk = riskWeight / items.length;
  const gap = naoAgir - prevenir;
  const topImpacts = [...impactCount.entries()]
    .sort((a, b) => b[1] - a[1])
    .map(([id]) => id);

  const suggestions: ActionSuggestion[] = [];

  for (const tpl of ACTION_TEMPLATES) {
    if (impact !== "todos" && tpl.impacts && !tpl.impacts.includes(impact)) {
      continue;
    }
    if (tpl.minRiskWeight != null && avgRisk < tpl.minRiskWeight - 0.35) {
      // still allow if filtered impact matches strongly
      if (!(impact !== "todos" && tpl.impacts?.includes(impact))) continue;
    }
    if (tpl.impacts) {
      const hits = tpl.impacts.reduce(
        (s, id) => s + (impactCount.get(id) ?? 0),
        0
      );
      if (hits === 0) continue;
    }
    if (tpl.prefersRegen) {
      const hits = tpl.prefersRegen.reduce((s, k) => s + regenCount[k], 0);
      if (hits === 0 && tpl.kind === "preservar") {
        // still show preserve lightly if moderate risk exists
        if (avgRisk > 2.2) continue;
      }
    }

    let priority = 10;
    priority += avgRisk * 8;
    priority += Math.min(maxTrend, 12);

    if (tpl.impacts) {
      for (const id of tpl.impacts) {
        const rank = topImpacts.indexOf(id);
        if (rank === 0) priority += 24;
        else if (rank === 1) priority += 14;
        else if (rank >= 0) priority += 6;
        if (impact === id) priority += 30;
      }
    }

    if (tpl.kind === "reverter") {
      priority += regenCount.a_recuperar * 4 + regenCount.em_regeneracao * 2;
      if (gap > 0) priority += Math.min(gap / 80, 20);
    }
    if (tpl.kind === "preservar") {
      priority +=
        (regenCount.protegido + regenCount.regenerado) * 5 +
        regenCount.em_regeneracao * 2;
      if (avgRisk <= 1.6) priority += 12;
    }
    if (tpl.kind === "retardar") {
      priority += avgRisk * 6 + Math.min(maxTrend, 10);
    }

    const related =
      tpl.impacts ??
      (impact !== "todos" ? [impact] : topImpacts.slice(0, 2));

    const metrics: ActionSuggestion["metrics"] = [
      {
        label: "View",
        value: `${items.length} ${levelLabel}${items.length === 1 ? "" : "s"}`,
      },
    ];

    if (tpl.kind === "reverter") {
      metrics.push(
        { label: "Eligible area", value: formatHa(areaHa) },
        { label: "Potential credits", value: formatCredits(creditos) },
        { label: "Inaction − prevent gap", value: formatBRL(gap) }
      );
    } else if (tpl.kind === "retardar") {
      metrics.push(
        { label: "Cost to prevent", value: formatBRL(prevenir) },
        { label: "If no action", value: formatBRL(naoAgir) }
      );
      if (related[0]) {
        metrics.push({
          label: "Target impact",
          value: IMPACT_LABELS[related[0]],
        });
      }
    } else {
      metrics.push(
        {
          label: "Already protected / restored",
          value: String(regenCount.protegido + regenCount.regenerado),
        },
        { label: "Regenerating", value: String(regenCount.em_regeneracao) }
      );
    }

    const whyParts = [
      `Prioritized for ${LEVEL_LABELS[level].toLowerCase()} level with current filters.`,
    ];
    if (impact !== "todos") {
      whyParts.push(`Impact filter: ${IMPACT_LABELS[impact]}.`);
    } else if (topImpacts[0]) {
      whyParts.push(
        `Most common impact in view: ${IMPACT_LABELS[topImpacts[0]]}.`
      );
    }

    suggestions.push({
      id: tpl.id,
      kind: tpl.kind,
      title: tpl.title,
      summary: tpl.summary,
      why: whyParts.join(" "),
      priority,
      metrics: metrics.slice(0, 3),
      relatedImpacts: related,
    });
  }

  return suggestions.sort((a, b) => b.priority - a.priority).slice(0, 4);
}
