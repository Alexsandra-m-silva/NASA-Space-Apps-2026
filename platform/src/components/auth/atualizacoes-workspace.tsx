"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { EmailTriggersCard } from "@/components/auth/email-triggers-card";
import { PreferenceForm } from "@/components/auth/preference-form";
import {
  ROLE_LABELS,
  defaultPreferences,
  normalizePreferences,
  type AlertPreferences,
  type UserProfile,
} from "@/data/alerts";
import { consumeExploreSeed } from "@/data/explore/seed-preferences";
import {
  useNewsletter,
  type StakeholderRole,
} from "@/lib/newsletter-context";

const ROLES = Object.keys(ROLE_LABELS) as StakeholderRole[];

function ChipToggle({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-md border px-2.5 py-1.5 text-left text-xs transition-colors ${
        active
          ? "border-primary bg-primary text-primary-foreground"
          : "border-border bg-card text-foreground hover:border-primary/40"
      }`}
    >
      {label}
    </button>
  );
}

export function AtualizacoesWorkspace() {
  const { subscription, ready, subscribe } = useNewsletter();
  const searchParams = useSearchParams();
  const fromExplore =
    searchParams.get("from") === "explore" ||
    searchParams.get("from") === "explorar";

  const [email, setEmail] = useState("");
  const [org, setOrg] = useState("");
  const [role, setRole] = useState<StakeholderRole>("gestor");
  const [prefs, setPrefs] = useState<AlertPreferences>(defaultPreferences());
  const [saved, setSaved] = useState(false);
  const [seededFromExplore, setSeededFromExplore] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const seed = fromExplore ? consumeExploreSeed() : null;
    if (seed) {
      setPrefs(normalizePreferences(seed.preferences));
      setSeededFromExplore(true);
    }
  }, [fromExplore]);

  useEffect(() => {
    if (!ready || !subscription || seededFromExplore) return;
    setEmail(subscription.email);
    setOrg(subscription.org ?? "");
    setRole(subscription.role);
    setPrefs(normalizePreferences(subscription.preferences));
  }, [ready, subscription, seededFromExplore]);

  const statusMessage = useMemo(() => {
    if (saved) {
      return "Subscription confirmed in this browser. The newsletter will follow the selection you set.";
    }
    if (seededFromExplore) {
      return "Your explore selection was pre-filled. Review it and confirm to start receiving the newsletter.";
    }
    return null;
  }, [saved, seededFromExplore]);

  function validateContact(): boolean {
    if (!email.trim() || !email.includes("@")) {
      setError("Enter a valid institutional or professional email.");
      return false;
    }
    if (!role) {
      setError("Select the role that best describes your work.");
      return false;
    }
    setError(null);
    return true;
  }

  function handleSubscribe(nextPrefs: AlertPreferences) {
    if (!validateContact()) return;
    const normalized = normalizePreferences({
      ...nextPrefs,
      alertsEnabled: true,
    });
    subscribe({
      email,
      role,
      org,
      preferences: normalized,
    });
    setPrefs(normalized);
    setSaved(true);
    setSeededFromExplore(false);
    window.setTimeout(() => setSaved(false), 2800);
  }

  return (
    <div
      data-header-contrast="light"
      className="mx-auto max-w-3xl space-y-8 px-4 py-12 sm:px-6 sm:py-16"
    >
      <div>
        <p className="text-[0.7rem] uppercase tracking-[0.18em] text-signal">
          Newsletter
        </p>
        <h1 className="mt-2 font-display text-3xl text-olive sm:text-4xl">
          Get updates when the territory changes
        </h1>
        <p className="mt-4 max-w-2xl text-sm leading-relaxed text-muted-foreground">
          You set the selection; we notify you when trend, risk, or impact
          changes.
        </p>
        {subscription?.preferences.alertsEnabled && (
          <p className="mt-2 text-xs text-muted-foreground">
            Active subscription · {subscription.email} ·{" "}
            {ROLE_LABELS[subscription.role as UserProfile["role"]]}
          </p>
        )}
      </div>

      <EmailTriggersCard />

      {statusMessage && (
        <p className="rounded-md border border-signal/30 bg-signal-soft px-4 py-3 text-sm text-olive">
          {statusMessage}
        </p>
      )}

      <section className="rounded-md border border-border bg-card/90 p-5 shadow-sm sm:p-8">
        <h2 className="font-display text-xl text-olive">
          Institutional contact
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          The email receives the newsletter. Your role shapes the framing —
          press, government, or business — without creating a platform account.
        </p>

        <div className="mt-6 space-y-4">
          <label className="block text-sm">
            <span className="mb-1 block text-xs uppercase tracking-[0.12em] text-muted-foreground">
              Professional email
            </span>
            <input
              type="email"
              className="h-10 w-full max-w-md rounded-md border border-input bg-background px-3"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              placeholder="name@agency.gov"
              required
            />
          </label>

          <label className="block text-sm">
            <span className="mb-1 block text-xs uppercase tracking-[0.12em] text-muted-foreground">
              Organization (optional)
            </span>
            <input
              className="h-10 w-full max-w-md rounded-md border border-input bg-background px-3"
              value={org}
              onChange={(e) => setOrg(e.target.value)}
              autoComplete="organization"
              placeholder="type here"
            />
          </label>

          <fieldset>
            <legend className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
              Role
            </legend>
            <p className="mt-2 text-xs text-muted-foreground">
              Choose what best describes how you use the evidence.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {ROLES.map((r) => (
                <ChipToggle
                  key={r}
                  label={ROLE_LABELS[r]}
                  active={role === r}
                  onClick={() => setRole(r)}
                />
              ))}
            </div>
          </fieldset>

          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>
      </section>

      <section className="rounded-md border border-border bg-card/90 p-5 shadow-sm sm:p-8">
        <h2 className="font-display text-xl text-olive">
          Monitoring selection
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Set territory, impacts, and risk levels. The same criteria used in
          Explore power the newsletter — useful for story ideas, public policy, or
          operational exposure.
        </p>

        <div className="mt-6">
          <PreferenceForm
            initial={prefs}
            submitLabel="Subscribe to the newsletter"
            cancelLabel="Cancel newsletter updates"
            onSubmit={handleSubscribe}
          />
        </div>
      </section>
    </div>
  );
}
