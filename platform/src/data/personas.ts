import type { Persona } from "./types";

export const personas: Persona[] = [
  {
    id: "gestor",
    name: "Federal or state manager",
    shortRole: "Civil defense / agriculture",
    priority: "p0",
    jobToBeDone:
      "Justify an amendment or PPA with cost of inaction versus cost to prevent.",
    context:
      "Works with state, biome, or program scopes. Needs average loss figures and an evidence package attachable to the budget brief — not another pretty map.",
    successMetric:
      "Package ready to attach to PPA/amendment with BRL risk, BRL prevent, and methodology note.",
    primaryOutput: "BRL average loss vs cost to prevent + evidence package",
    accent: "gestor",
  },
  {
    id: "prefeito",
    name: "Mayor or municipal secretary",
    shortRole: "Municipality in emergency",
    priority: "p0",
    jobToBeDone:
      "Get surface trend in your area, a policy template, and order-of-magnitude local loss — with term time ahead, not at SMS alert time.",
    context:
      "Municipality already declared emergency or is on the risk list. The political horizon is remaining term years, not the 20-year science cycle.",
    successMetric:
      "Documented municipal decision (text + number) before the SMS crisis.",
    primaryOutput:
      "Local trend + policy template + order-of-magnitude loss",
    accent: "prefeito",
  },
  {
    id: "assessor",
    name: "Parliamentary staff / rapporteur aide",
    shortRole: "Amendment and report",
    priority: "p0",
    jobToBeDone:
      "Attach numbers to an amendment or report the same day, with auditable sources.",
    context:
      "Does not operate Climate Sentinel day to day. Builds the attachment from municipality/state or an amendment draft and needs to compare 2–3 scopes to prioritize.",
    successMetric: "One-pager + cost-of-inaction table usable in a report.",
    primaryOutput: "One-pager + sources + cost-of-inaction table",
    accent: "assessor",
  },
  {
    id: "jornalista",
    name: "Data journalist / editor",
    shortRole: "Evidence for the story",
    priority: "p0",
    jobToBeDone:
      "Tell the story with auditable evidence — what the radar shows, what the projection implies, and what cannot be claimed.",
    context:
      "Enters via topic (desertification, emergency, biome) or emblematic municipality. Needs methodology, NISAR limits, and publication kit, not a fiscal dashboard.",
    successMetric:
      "Story or thread with quote-ready findings, charts, and reproducible stable link.",
    primaryOutput:
      "Package: map, time series, methodology, quote-ready findings",
    accent: "jornalista",
  },
  {
    id: "familia",
    name: "Family in a risk area",
    shortRole: "Awareness / local pressure",
    priority: "stretch",
    jobToBeDone:
      "Understand what is changing nearby and what to ask city hall for — without becoming a fiscal Climate Sentinel user.",
    context:
      "Arrives via link shared by the municipality or social card. Pressure and awareness channel; does not write PPAs.",
    successMetric: "Shared \"your area\" card + handoff to official channel.",
    primaryOutput: "Shareable \"your area at risk\" card",
    accent: "familia",
  },
];

export function getPersona(id: string): Persona | undefined {
  return personas.find((p) => p.id === id);
}

export const primaryPersonas = personas.filter((p) => p.priority === "p0");