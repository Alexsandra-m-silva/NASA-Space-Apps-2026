export interface GridPosition {
  column: number;
  row: number;
}

export interface MissionChoice {
  label: string;
  correct: boolean;
  feedback: string;
}

export interface MissionStep {
  title: string;
  area: string;
  prompt: string;
  clue: string;
  target: GridPosition;
  choices: readonly MissionChoice[];
}

export const START_POSITION: GridPosition = { column: 1, row: 3 };

export const LEARN_GAME_STEPS: readonly MissionStep[] = [
  {
    title: "Dance with SARs",
    area: "Radar ridge",
    prompt: "How will you read the radar signal?",
    clue: "Two passes cross this dry-season landscape. A single image can be misleading.",
    target: { column: 2, row: 2 },
    choices: [
      {
        label: "Compare same-track radar passes",
        correct: true,
        feedback:
          "Right call. Comparing consistent passes helps separate real surface change from viewing geometry and seasonal noise.",
      },
      {
        label: "Trust one radar snapshot",
        correct: false,
        feedback:
          "One snapshot cannot show change over time. Compare consistent passes before drawing a conclusion.",
      },
    ],
  },
  {
    title: "Detect desertification",
    area: "Dryland study plot",
    prompt: "Which area deserves a closer look?",
    clue: "Some vegetation loss repeats across years; other bare patches appear only in the dry season.",
    target: { column: 6, row: 2 },
    choices: [
      {
        label: "Map persistent vegetation decline",
        correct: true,
        feedback:
          "Good detection. Persistent decline is a stronger signal to investigate than a single dry-season observation.",
      },
      {
        label: "Mark every dry-season patch as desert",
        correct: false,
        feedback:
          "Seasonal dryness alone is not enough. Check the longer-term vegetation trend and local context.",
      },
    ],
  },
  {
    title: "Call for partners",
    area: "Community meeting point",
    prompt: "Who should help decide what happens next?",
    clue: "People who live and work here know the land, its needs, and what restoration can sustain.",
    target: { column: 6, row: 5 },
    choices: [
      {
        label: "Bring local communities and scientists together",
        correct: true,
        feedback:
          "Exactly. Local knowledge and scientific evidence make a stronger, more grounded plan.",
      },
      {
        label: "Plan the intervention alone",
        correct: false,
        feedback:
          "A plan made without local partners can miss the area's needs. Invite the community into the decision.",
      },
    ],
  },
  {
    title: "Restore the land",
    area: "Caatinga restoration plot",
    prompt: "What is a thoughtful first step for this landscape?",
    clue: "This is a water-limited Caatinga ecosystem. Native species are adapted to its conditions.",
    target: { column: 2, row: 5 },
    choices: [
      {
        label: "Restore with native Caatinga plants and follow up",
        correct: true,
        feedback:
          "The plot is growing. Native plants and long-term care give this restoration a better chance to take root.",
      },
      {
        label: "Plant thirsty fast-growing trees everywhere",
        correct: false,
        feedback:
          "More planting is not always better. Choose species suited to local water and habitat conditions.",
      },
    ],
  },
];

export function isNearTarget(
  position: GridPosition,
  target: GridPosition
): boolean {
  return (
    Math.abs(position.column - target.column) +
      Math.abs(position.row - target.row) <=
    2
  );
}
