"use client";

import { useState, type KeyboardEvent, type ReactNode } from "react";
import {
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  Check,
  RotateCcw,
  Sparkles,
} from "lucide-react";
import {
  LEARN_GAME_STEPS,
  START_POSITION,
  isNearTarget,
  type GridPosition,
  type MissionChoice,
} from "@/data/learn-game";
import { Button } from "@/components/ui/button";
import { WebXRWorld } from "@/components/learn-game/webxr-world";

const MOVE_KEYS: Record<string, [number, number]> = {
  ArrowUp: [0, -1],
  w: [0, -1],
  W: [0, -1],
  ArrowDown: [0, 1],
  s: [0, 1],
  S: [0, 1],
  ArrowLeft: [-1, 0],
  a: [-1, 0],
  A: [-1, 0],
  ArrowRight: [1, 0],
  d: [1, 0],
  D: [1, 0],
};

function moveWithinWorld(position: GridPosition): GridPosition {
  return {
    column: Math.max(0, Math.min(8, position.column)),
    row: Math.max(0, Math.min(6, position.row)),
  };
}

export function LearnGame() {
  const [position, setPosition] = useState(START_POSITION);
  const [stageIndex, setStageIndex] = useState(0);
  const [feedback, setFeedback] = useState<{
    correct: boolean;
    message: string;
  } | null>(null);
  const [xrActive, setXrActive] = useState(false);
  const [xrSupported, setXrSupported] = useState<boolean | null>(null);

  const complete = stageIndex >= LEARN_GAME_STEPS.length;
  const activeStep =
    LEARN_GAME_STEPS[Math.min(stageIndex, LEARN_GAME_STEPS.length - 1)];
  const nearby = isNearTarget(position, activeStep.target);

  const moveTo = (next: GridPosition) => setPosition(moveWithinWorld(next));

  const moveBy = (columnDelta: number, rowDelta: number) => {
    moveTo({
      column: position.column + columnDelta,
      row: position.row + rowDelta,
    });
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const movement = MOVE_KEYS[event.key];
    if (!movement) return;
    event.preventDefault();
    moveBy(movement[0], movement[1]);
  };

  const chooseAction = (choice: MissionChoice) => {
    if (!nearby) return;
    setFeedback({ correct: choice.correct, message: choice.feedback });
    if (choice.correct) setStageIndex((current) => current + 1);
  };

  const restart = () => {
    setPosition(START_POSITION);
    setStageIndex(0);
    setFeedback(null);
  };

  return (
    <section className="mx-auto min-h-[calc(100svh-3.75rem)] max-w-7xl px-4 pb-10 pt-6 sm:px-6 sm:pt-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-ocre">
            Desert Sentinel · Field mission
          </p>
          <h1 className="font-display text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
            Learn by playing
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground sm:text-base">
            Explore a 3D Caatinga landscape on desktop or enter immersive
            WebXR. Read the clues, make evidence-based choices, and help a
            restoration plot grow.
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-border bg-card/80 px-3 py-2 text-xs font-medium text-muted-foreground">
          <span
            className={`h-2 w-2 rounded-full ${
              xrActive ? "bg-[#66844e]" : "bg-[#d5a945]"
            }`}
          />
          {xrActive
            ? "Immersive WebXR active"
            : xrSupported === null
              ? "Checking WebXR support…"
              : xrSupported
                ? "WebXR headset available"
                : "WebXR headset not detected"}
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1.55fr)_minmax(300px,0.8fr)]">
        <div className="min-w-0">
          <div className="overflow-hidden rounded-2xl border border-[#70543a]/20 bg-[#a9d0ce] shadow-[0_20px_60px_-32px_rgba(34,15,8,0.55)]">
            <WebXRWorld
              position={position}
              target={activeStep.target}
              stage={stageIndex}
              step={activeStep}
              choices={activeStep.choices}
              canChoose={nearby}
              restored={complete}
              feedback={feedback}
              onMove={moveTo}
              onChoose={chooseAction}
              onKeyDown={handleKeyDown}
              onXRActiveChange={setXrActive}
              onXRSupportChange={setXrSupported}
            />
            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[#70543a]/15 bg-[#fffaf0] px-4 py-3">
              <p className="text-xs font-medium text-[#594634]">
                Move: select a tile · WASD or arrows · VR: point and trigger
              </p>
              <div className="flex items-center gap-2 text-xs text-[#594634]">
                <span className="inline-block h-2.5 w-2.5 rounded-full bg-[#f1c84e]" />
                Mission signal
                <span className="ml-2 inline-block h-2.5 w-2.5 rounded-full bg-[#678950]" />
                Restoration
              </div>
            </div>
          </div>

          <div className="mt-3 flex items-center justify-between gap-4 rounded-xl border border-border/70 bg-card/70 p-3">
            <p className="text-xs leading-5 text-muted-foreground">
              {nearby || complete
                ? "You are close enough to inspect this area."
                : `Walk toward ${activeStep.area} to unlock its choices.`}
            </p>
            <div className="grid grid-cols-3 gap-1" aria-label="Movement controls">
              <span />
              <MoveButton label="Move north" onClick={() => moveBy(0, -1)}>
                <ArrowUp />
              </MoveButton>
              <span />
              <MoveButton label="Move west" onClick={() => moveBy(-1, 0)}>
                <ArrowLeft />
              </MoveButton>
              <MoveButton label="Move south" onClick={() => moveBy(0, 1)}>
                <ArrowDown />
              </MoveButton>
              <MoveButton label="Move east" onClick={() => moveBy(1, 0)}>
                <ArrowRight />
              </MoveButton>
            </div>
          </div>
          <p className="mt-2 px-1 text-xs leading-5 text-muted-foreground">
            Immersive VR requires a WebXR-capable browser and headset, served
            from localhost or an HTTPS origin.
          </p>
        </div>

        <div
          className="flex flex-col rounded-2xl border border-border bg-card/90 p-5 shadow-sm sm:p-6"
        >
          <div className="mb-5 flex items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                Mission progress
              </p>
              <p className="mt-1 text-sm font-semibold text-foreground">
                {complete
                  ? "Mission complete"
                  : `Step ${stageIndex + 1} of ${LEARN_GAME_STEPS.length}`}
              </p>
            </div>
            {complete ? (
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-[#e6eedb] text-[#45633b]">
                <Sparkles aria-hidden="true" className="h-5 w-5" />
              </span>
            ) : (
              <span className="text-xs font-medium text-muted-foreground">
                {stageIndex}/{LEARN_GAME_STEPS.length} complete
              </span>
            )}
          </div>

          <div
            className="mb-6 grid grid-cols-4 gap-1.5"
            aria-label={`${stageIndex} of ${LEARN_GAME_STEPS.length} steps completed`}
          >
            {LEARN_GAME_STEPS.map((step, index) => (
              <div
                key={step.title}
                className={`h-1.5 rounded-full ${
                  index < stageIndex ? "bg-[#66844e]" : "bg-secondary"
                }`}
              />
            ))}
          </div>

          {complete ? (
            <div className="flex flex-1 flex-col">
              <div className="rounded-xl border border-[#d6e0c8] bg-[#f1f5e9] p-4">
                <div className="mb-2 flex items-center gap-2 font-semibold text-[#38583a]">
                  <Check aria-hidden="true" className="h-5 w-5" />
                  The restoration plot is growing
                </div>
                <p className="text-sm leading-6 text-[#4e5e47]">
                  You compared radar evidence, checked long-term vegetation
                  signals, partnered with the community, and chose native
                  plants. Keep monitoring: restoration takes time.
                </p>
              </div>
              <div className="mt-auto pt-6">
                <Button onClick={restart} variant="outline" className="w-full">
                  <RotateCcw aria-hidden="true" />
                  Play again
                </Button>
              </div>
            </div>
          ) : (
            <>
              <div className="mb-5">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-ocre">
                  {activeStep.area}
                </p>
                <h2 className="mt-1 font-display text-2xl font-semibold text-foreground">
                  {activeStep.title}
                </h2>
                <p className="mt-3 text-sm font-medium leading-6 text-foreground">
                  {activeStep.prompt}
                </p>
                <p className="mt-2 rounded-lg bg-secondary/70 px-3 py-2.5 text-xs leading-5 text-muted-foreground">
                  Field clue: {activeStep.clue}
                </p>
              </div>

              {feedback ? (
                <p
                  role="status"
                  aria-live="polite"
                  className={`mb-4 rounded-lg px-3 py-2.5 text-sm leading-5 ${
                    feedback.correct
                      ? "bg-[#edf3e6] text-[#38583a]"
                      : "bg-[#f8e9df] text-[#783e26]"
                  }`}
                >
                  {feedback.message}
                </p>
              ) : null}

              <div className="mt-auto space-y-2.5">
                {activeStep.choices.map((choice) => (
                  <Button
                    key={choice.label}
                    onClick={() => chooseAction(choice)}
                    disabled={!nearby}
                    variant="outline"
                    className="h-auto min-h-12 w-full justify-start whitespace-normal px-3 py-3 text-left leading-5"
                  >
                    {choice.label}
                  </Button>
                ))}
                {!nearby ? (
                  <p className="pt-1 text-center text-xs text-muted-foreground">
                    Get closer to the yellow signal to choose an action.
                  </p>
                ) : null}
              </div>
            </>
          )}
        </div>
      </div>
    </section>
  );
}

function MoveButton({
  label,
  onClick,
  children,
}: {
  label: string;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <Button
      type="button"
      size="icon"
      variant="outline"
      aria-label={label}
      className="h-8 w-8 bg-card/90"
      onClick={onClick}
    >
      {children}
    </Button>
  );
}
