export type PersonaId =
  | "gestor"
  | "prefeito"
  | "assessor"
  | "jornalista"
  | "familia";

export type PersonaPriority = "p0" | "stretch";

export type FlowStep = {
  id: string;
  title: string;
  phase: string;
  objective: string;
  dataOnScreen: string[];
  decision: string;
  cta: string;
  nextHint: string;
  sampleUi: {
    headline: string;
    metrics?: { label: string; value: string }[];
    bullets?: string[];
  };
};

export type Persona = {
  id: PersonaId;
  name: string;
  shortRole: string;
  priority: PersonaPriority;
  jobToBeDone: string;
  context: string;
  successMetric: string;
  primaryOutput: string;
  accent: string;
};

export type SpineNode = {
  id: string;
  label: string;
  detail: string;
};

export type CompareOutput = {
  personaId: PersonaId;
  framing: string;
  exportLabel: string;
};
