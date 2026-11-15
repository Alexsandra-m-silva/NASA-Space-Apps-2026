import type { FlowStep, PersonaId } from "./types";

export const flows: Record<PersonaId, FlowStep[]> = {
  gestor: [
    {
      id: "entrada",
      title: "Enter via institutional scope",
      phase: "Entry",
      objective:
        "Reach Desert Sentinel from your work context (state, biome, or program) without hunting municipalities at random.",
      dataOnScreen: [
        "Deep link or selector: state / biome / program",
        "Scope summary: municipality count, average NISAR trend",
        'Shortcut for "municipalities in emergency"',
      ],
      decision: "Which scope justifies this week’s budget brief?",
      cta: "Open scope",
      nextHint: "Explore ranking and map for the chosen scope",
      sampleUi: {
        headline: "Scope: Semi-arid — state civil defense",
        metrics: [
          { label: "Municipalities in scope", value: "187" },
          { label: "In emergency", value: "24" },
          { label: "NISAR trend (12m)", value: "+6.2%" },
        ],
        bullets: [
          "Institutional entry, not a generic landing",
          "Last exported package 11 days ago",
        ],
      },
    },
    {
      id: "explorar",
      title: "Explore map and risk ranking",
      phase: "Explore",
      objective:
        "See where surface trend and BRL risk concentrate to prioritize the argument.",
      dataOnScreen: [
        "Choropleth map: NISAR trend + index",
        "Ranking: municipality × trend × 10-year BRL risk",
        "Filters: emergency, biome, loss band",
      ],
      decision: "Which municipalities go into the amendment/PPA justification?",
      cta: "Select for justification",
      nextHint: "Open inaction vs prevention cost panel",
      sampleUi: {
        headline: "Ranking by BRL risk (10 years)",
        metrics: [
          { label: "Top municipality", value: "R$ 48 mi" },
          { label: "Scope median", value: "R$ 6.1 mi" },
        ],
        bullets: [
          "Surface trend × expected loss crossover",
          "Multi-select for the evidence package",
        ],
      },
    },
    {
      id: "justificar",
      title: "Justify: inaction vs prevention",
      phase: "Justify",
      objective:
        "Translate the trajectory into BRL over 5 / 10 / 20 years and compare with prevention cost.",
      dataOnScreen: [
        "5 / 10 / 20 year table: expected average loss",
        "Estimated cost of prevention package",
        "Projected flora and fauna effect (summary)",
      ],
      decision: "Does the BRL risk − BRL prevent gap support the amendment?",
      cta: "Build evidence package",
      nextHint: "Export PDF/CSV + methodology note",
      sampleUi: {
        headline: "Cost of inaction × cost to prevent",
        metrics: [
          { label: "Inaction (10 years)", value: "R$ 412 mi" },
          { label: "Prevent (package)", value: "R$ 97 mi" },
          { label: "Flora/fauna under pressure", value: "18 spp." },
        ],
        bullets: [
          "Horizon toggle: 5 / 10 / 20 years",
          "Explicit uncertainty interval",
        ],
      },
    },
    {
      id: "exportar",
      title: "Export for PPA / amendment",
      phase: "Export",
      objective:
        "Leave with a usable attachment: numbers, summary map, and methodology note.",
      dataOnScreen: [
        "PDF preview (cover + table + sources)",
        "CSV of selected municipalities",
        "Methodology note (NISAR → index → BRL)",
      ],
      decision: "Is the package complete for the budget brief?",
      cta: "Download package",
      nextHint: "Success: attach to amendment/PPA",
      sampleUi: {
        headline: "Evidence package — civil defense",
        bullets: [
          "6-page PDF + CSV",
          "Index version and date in footer",
          "Suggested citation for justification",
        ],
      },
    },
    {
      id: "sucesso",
      title: "Success: brief justified",
      phase: "Success",
      objective:
        "Confirm the manager left with attachable material — not just “explored the map.”",
      dataOnScreen: [
        "Checklist of what was exported",
        "Stable scope link for the team",
        "Next estimated NISAR update",
      ],
      decision: "Send to budget review or revise selection?",
      cta: "Copy scope link",
      nextHint: "End of P0 manager flow",
      sampleUi: {
        headline: "Package ready to attach",
        metrics: [
          { label: "Municipalities in attachment", value: "12" },
          { label: "10-year gap", value: "R$ 315 mi" },
        ],
      },
    },
  ],

  prefeito: [
    {
      id: "entrada",
      title: "Enter via municipality in emergency",
      phase: "Entry",
      objective:
        "Go straight to the municipality sheet — curated emergency list or search.",
      dataOnScreen: [
        "Municipalities with emergency decree",
        "Search by name / IBGE",
        '“Sample data” badge if mock',
      ],
      decision: "Is this my municipality (or the secretary’s)?",
      cta: "Open municipality sheet",
      nextHint: "View trend and term horizon",
      sampleUi: {
        headline: "Municipalities in emergency — sample",
        bullets: [
          "Jaguaribe (CE) — decree 40 days ago",
          "Tauá (CE) — decree 12 days ago",
          "Search: type municipality name",
        ],
      },
    },
    {
      id: "orientar",
      title: "Orient within the term",
      phase: "Orient",
      objective:
        "Show local surface trend and what changes in remaining term years — not only over 20 years.",
      dataOnScreen: [
        "NISAR trend in municipality area",
        "Political horizon: remaining term years",
        "Order-of-magnitude local loss (Desert Sentinel)",
      ],
      decision: "Does the risk fit my term or only “after I’m gone”?",
      cta: "View possible actions",
      nextHint: "Open prioritized policy template",
      sampleUi: {
        headline: "Jaguaribe — what changes in your term",
        metrics: [
          { label: "Term years ahead", value: "2.5" },
          { label: "Surface trend", value: "+8.4%" },
          { label: "Local loss (order)", value: "R$ 9–14 mi" },
        ],
      },
    },
    {
      id: "agir",
      title: "Act with policy template",
      phase: "Act",
      objective:
        "Get 3–5 prioritized measures with order-of-magnitude cost and expected effect.",
      dataOnScreen: [
        "Prioritized measure list (template)",
        "Approximate cost × 5-year effect",
        "Dependencies: state, federal government, consortium",
      ],
      decision: "Which package fits the budget and local capacity?",
      cta: "Generate decision sheet",
      nextHint: "Forward evidence to state / caucus",
      sampleUi: {
        headline: "Policy template — 4 measures",
        bullets: [
          "1. Erosion control in critical areas",
          "2. Recovery of priority springs",
          "3. Grazing zoning",
          "4. Coordination with state civil defense",
        ],
      },
    },
    {
      id: "encaminhar",
      title: "Escalate upward",
      phase: "Share up",
      objective:
        "Send evidence to state or caucus with ready text + numbers.",
      dataOnScreen: [
        "Draft memo / email template",
        "Short attachment (1–2 pages)",
        "Suggested contacts (state / reps in scope)",
      ],
      decision: "Who needs to sign or receive this now?",
      cta: "Copy memo + download attachment",
      nextHint: "Success: decision documented in term",
      sampleUi: {
        headline: "Forwarding to state",
        bullets: [
          "Pre-filled memo with BRL and trend",
          "Desert Sentinel attachment (municipality version)",
        ],
      },
    },
    {
      id: "sucesso",
      title: "Success: decision before the SMS",
      phase: "Success",
      objective:
        "Record that a decision was made with text + number — prevention, not just alert response.",
      dataOnScreen: [
        "Summary of chosen decision",
        "Review reminder (next NISAR update)",
        "Link to public awareness card (family stretch)",
      ],
      decision: "Archive, share with cabinet, or generate public card?",
      cta: "Save decision sheet",
      nextHint: "End of P0 mayor flow",
      sampleUi: {
        headline: "Municipal decision recorded",
        metrics: [
          { label: "Measures chosen", value: "3" },
          { label: "Horizon", value: "term" },
        ],
      },
    },
  ],

  assessor: [
    {
      id: "entrada",
      title: "Enter via amendment or territory",
      phase: "Entry",
      objective:
        "Start from an amendment draft or a municipality/state already on the office agenda.",
      dataOnScreen: [
        "Field: amendment number/topic (optional)",
        "Municipality / state search",
        "Recent office scopes",
      ],
      decision: "Build the attachment from where?",
      cta: "Assemble one-pager",
      nextHint: "Build problem → BRL → action narrative",
      sampleUi: {
        headline: "New amendment — Desert Sentinel attachment",
        bullets: [
          "Amendment not numbered yet",
          "Territory: 3 municipalities in Cariri",
        ],
      },
    },
    {
      id: "montar",
      title: "Assemble the one-pager",
      phase: "Assemble",
      objective:
        "Problem → NISAR trend → BRL → action → source, on one page.",
      dataOnScreen: [
        "Editable one-pager blocks",
        "Cost of inaction table (5/10/20)",
        "Source citation and index version",
      ],
      decision: "Does the narrative fit on one page without losing the number?",
      cta: "Preview one-pager",
      nextHint: "Compare 2–3 scopes to prioritize",
      sampleUi: {
        headline: "One-pager — structure",
        bullets: [
          "Local problem in 2 lines",
          "Surface trend + index",
          "BRL inaction vs prevent",
          "Recommended action + NISAR source",
        ],
      },
    },
    {
      id: "comparar",
      title: "Compare scopes to prioritize",
      phase: "Compare",
      objective:
        "Put 2–3 scopes side by side and choose what best supports the amendment.",
      dataOnScreen: [
        "Comparison cards (trend, BRL, flora/fauna)",
        "“Evidence strength” indicator",
        "Note if data is sample",
      ],
      decision: "Which scope goes in the main attachment?",
      cta: "Set amendment scope",
      nextHint: "Export PDF and short slides",
      sampleUi: {
        headline: "Compare 3 scopes",
        metrics: [
          { label: "Largest BRL gap", value: "Scope B" },
          { label: "Strongest trend", value: "Scope A" },
        ],
      },
    },
    {
      id: "exportar",
      title: "Export today’s attachment",
      phase: "Export",
      objective: "Leave with one-pager PDF and 3–5 slides for the rapporteur.",
      dataOnScreen: [
        "One-pager PDF",
        "Short slides (problem / number / ask)",
        "Sources checklist",
      ],
      decision: "Ready to paste into the report today?",
      cta: "Download PDF + slides",
      nextHint: "Success: same-day attachment",
      sampleUi: {
        headline: "Office export",
        bullets: ["1-page PDF", "5 slides", "Optional CSV"],
      },
    },
    {
      id: "sucesso",
      title: "Success: attachment in the report",
      phase: "Success",
      objective: "Confirm use in the legislative flow — not just download.",
      dataOnScreen: [
        "Stable one-pager link",
        "Version history",
        "Suggested wording for the report",
      ],
      decision: "Forward to rapporteur or adjust text?",
      cta: "Copy stable link",
      nextHint: "End of P0 staffer flow",
      sampleUi: {
        headline: "Ready for the report",
        metrics: [{ label: "Estimated assembly time", value: "< 1h" }],
      },
    },
  ],

  jornalista: [
    {
      id: "entrada",
      title: "Enter via topic or emblematic municipality",
      phase: "Entry",
      objective:
        "Arrive through the beat — desertification, emergency, biome — without institutional login.",
      dataOnScreen: [
        "Featured topics",
        "Emblematic municipalities (sample)",
        "Notice: sample data in this phase",
      ],
      decision: "What angle for the story?",
      cta: "Open investigation",
      nextHint: "Explore time series and projections",
      sampleUi: {
        headline: "Beats with Desert Sentinel evidence",
        bullets: [
          "Emergencies and surface trend",
          "Semi-arid: 10 years of pressure",
          "What NISAR sees that the eye does not",
        ],
      },
    },
    {
      id: "investigar",
      title: "Investigate trend and projection",
      phase: "Investigate",
      objective:
        "View time series, map, projected flora/fauna and uncertainty — reporting material.",
      dataOnScreen: [
        "Surface trend time series",
        "Map of story scope",
        "Flora/fauna projection 5 / 10 / 20 + uncertainty band",
      ],
      decision: "Is there a strong enough finding for the lede?",
      cta: "Mark findings",
      nextHint: "Verify methodology and limits",
      sampleUi: {
        headline: "Candidate finding",
        metrics: [
          { label: "36m acceleration", value: "+2.1 pp" },
          { label: "Species under pressure (10y)", value: "11" },
        ],
        bullets: ["Uncertainty: ±18% on projected BRL"],
      },
    },
    {
      id: "verificar",
      title: "Verify what you cannot claim",
      phase: "Verify",
      objective:
        "Read methodology, radar limits, and what Desert Sentinel does not attribute causally.",
      dataOnScreen: [
        "Short methodology sheet",
        "NISAR limits (what it measures / does not)",
        '“Do not say this” list for the desk',
      ],
      decision: "Which sentences survive fact-check?",
      cta: "Generate publication kit",
      nextHint: "Download quote-ready kit",
      sampleUi: {
        headline: "Explicit limits",
        bullets: [
          "Radar sees surface change, not individual “blame”",
          "BRL is modeled order of magnitude, not an audit",
          "Flora/fauna: habitat pressure, not a census",
        ],
      },
    },
    {
      id: "kit",
      title: "Publication kit",
      phase: "Publish kit",
      objective:
        "Leave with quote-ready findings, charts, credits, and stable link.",
      dataOnScreen: [
        "Quote-ready sentences (with context)",
        "Exportable charts + credits",
        "Stable evidence link",
      ],
      decision: "Does the kit close the story or the thread?",
      cta: "Download kit",
      nextHint: "Success: reproducible evidence",
      sampleUi: {
        headline: "Kit for the newsroom",
        bullets: [
          "3 findings with source and date",
          "2 PNG/SVG charts",
          "NISAR / Desert Sentinel credits block",
        ],
      },
    },
    {
      id: "sucesso",
      title: "Success: evidence in the story",
      phase: "Success",
      objective:
        "Publish with reproducible link — without becoming a manager dashboard.",
      dataOnScreen: [
        "Stable link for readers",
        "Summary of what was cited",
        "Channel for correction / update",
      ],
      decision: "Publish, request technical interview, or revise findings?",
      cta: "Copy link for readers",
      nextHint: "End of P0 journalist flow",
      sampleUi: {
        headline: "Ready to publish",
        metrics: [{ label: "Findings in kit", value: "3" }],
      },
    },
  ],

  familia: [
    {
      id: "entrada",
      title: "Arrive via shared link",
      phase: "Entry",
      objective:
        'Open a “your area” card from city hall or social share — no login.',
      dataOnScreen: [
        "Municipality name / approximate neighborhood",
        "Plain language (no PPA jargon)",
        "Link source (city hall / share)",
      ],
      decision: "Is this about my region?",
      cta: "See what is changing",
      nextHint: "Understand nearby change and what to ask for",
      sampleUi: {
        headline: "Your area — Jaguaribe",
        bullets: [
          "Link sent by city hall",
          "No sign-up",
        ],
      },
    },
    {
      id: "entender",
      title: "Understand change near you",
      phase: "Awareness",
      objective:
        "See, in clear language, surface trend and risk for the surroundings — no fiscal table.",
      dataOnScreen: [
        "Short trend explanation",
        "What may affect local flora/fauna (summary)",
        "What city hall already logged in Desert Sentinel",
      ],
      decision: "Want to know what to ask city hall?",
      cta: "See what to ask for",
      nextHint: "Accountability and sharing actions",
      sampleUi: {
        headline: "The land is changing faster here",
        bullets: [
          "More exposed soil in recent years (radar)",
          "Pressure on native vegetation nearby",
        ],
      },
    },
    {
      id: "cobrar",
      title: "Hold accountable and share",
      phase: "Pressure",
      objective:
        "Know what to ask city hall and share the card — pressure channel, not a dashboard.",
      dataOnScreen: [
        "Suggested questions for city hall",
        "Official channel link",
        "Shareable card",
      ],
      decision: "Share, open official channel, or just save?",
      cta: "Share card",
      nextHint: "Stretch: awareness without fiscal flow",
      sampleUi: {
        headline: "What you can ask for",
        bullets: [
          "Is there a municipal plan with a deadline this term?",
          "Which critical areas were prioritized?",
          "Share on X / WhatsApp",
        ],
      },
    },
  ],
};

export function getFlow(personaId: string): FlowStep[] | undefined {
  if (personaId in flows) {
    return flows[personaId as PersonaId];
  }
  return undefined;
}

export function getStep(
  personaId: string,
  stepId: string
): FlowStep | undefined {
  return getFlow(personaId)?.find((s) => s.id === stepId);
}