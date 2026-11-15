"use client";

import { useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { PreferenceForm } from "@/components/auth/preference-form";
import { EmailTriggersCard } from "@/components/auth/email-triggers-card";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  defaultPreferences,
  type AlertPreferences,
} from "@/data/alerts";
import { personas } from "@/data/personas";
import {
  useNewsletter,
  type NewsletterSubscription,
} from "@/lib/newsletter-context";
import { readExploreSeed } from "@/data/explore/seed-preferences";

function preferencesFromSubscription(
  sub: NewsletterSubscription | null
): AlertPreferences {
  if (!sub) return defaultPreferences;
  return {
    ...defaultPreferences,
    ...sub.preferences,
    channels: { ...defaultPreferences.channels, ...sub.preferences.channels },
  };
}

export function AtualizacoesWorkspace() {
  const searchParams = useSearchParams();
  const fromExplore = searchParams.get("from") === "explore";
  const { subscription, ready, subscribe } = useNewsletter();

  const [email, setEmail] = useState("");
  const [institution, setInstitution] = useState("");
  const [role, setRole] = useState<string>("prefeitura");
  const [prefs, setPrefs] = useState<AlertPreferences>(defaultPreferences);
  const [hydrated, setHydrated] = useState(false);
  const [successOpen, setSuccessOpen] = useState(false);

  useMemo(() => {
    if (!ready || hydrated) return null;
    const seed = fromExplore ? readExploreSeed() : null;
    setEmail(subscription?.email ?? "");
    setInstitution(subscription?.institution ?? "");
    setRole(subscription?.role ?? seed?.role ?? "prefeitura");
    setPrefs(
      subscription
        ? preferencesFromSubscription(subscription)
        : seed?.preferences ?? defaultPreferences
    );
    setHydrated(true);
    return null;
  }, [ready, hydrated, subscription, fromExplore]);

  const intro = useMemo(() => {
    if (fromExplore && !subscription) {
      return "Your explore selection was pre-filled. Review it and confirm to start receiving the newsletter.";
    }
    if (subscription) {
      return "Update contact or criteria anytime. Saves stay in this browser for the prototype.";
    }
    return "Choose contact and criteria. You are notified when the evidence in your selection actually changes.";
  }, [fromExplore, subscription]);

  function handleSubscribe(nextPrefs: AlertPreferences) {
    const trimmed = email.trim();
    if (!trimmed) {
      window.alert("Enter an email to receive the newsletter.");
      return;
    }
    subscribe({
      email: trimmed,
      institution: institution.trim(),
      role,
      preferences: nextPrefs,
      updatedAt: new Date().toISOString(),
    });
    setPrefs(nextPrefs);
    setSuccessOpen(true);
  }

  if (!ready || !hydrated) {
    return (
      <p className="text-sm text-muted-foreground">Loading newsletter…</p>
    );
  }

  return (
    <div className="space-y-10">
      <header className="max-w-2xl">
        <p className="text-[0.7rem] uppercase tracking-[0.2em] text-signal">
          Newsletter
        </p>
        <h1 className="mt-2 font-display text-3xl text-olive sm:text-4xl">
          Monitor the ground that matters to you
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
          {intro}
        </p>
      </header>

      <section className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="space-y-6 rounded-lg border border-border bg-card/60 p-5 sm:p-6">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2 sm:col-span-2">
              <Label htmlFor="nl-email">Email</Label>
              <Input
                id="nl-email"
                type="email"
                autoComplete="email"
                placeholder="you@organization.gov.br"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div className="space-y-2 sm:col-span-2">
              <Label htmlFor="nl-institution">Institution</Label>
              <Input
                id="nl-institution"
                placeholder="City hall, newsroom, NGO…"
                value={institution}
                onChange={(e) => setInstitution(e.target.value)}
              />
            </div>
            <div className="space-y-2 sm:col-span-2">
              <Label>Role</Label>
              <Select value={role} onValueChange={setRole}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a role" />
                </SelectTrigger>
                <SelectContent>
                  {personas.map((p) => (
                    <SelectItem key={p.id} value={p.id}>
                      {p.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                The email receives the newsletter. Your role shapes the framing —
                cabinet brief, story angle, or field note.
              </p>
            </div>
          </div>

          <PreferenceForm
            value={prefs}
            onChange={setPrefs}
            submitLabel="Subscribe to the newsletter"
            cancelLabel="Cancel newsletter updates"
            onSubmit={handleSubscribe}
          />
        </div>

        <EmailTriggersCard preferences={prefs} />
      </section>

      <section className="rounded-lg border border-border bg-secondary/40 p-5 sm:p-6">
        <h2 className="font-display text-lg text-olive">What you get</h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground">
          Same evidence stack as Explore — territory, trend, risk, impact, and
          suggested actions — delivered when your criteria move. Filters from
          Explore power the newsletter — useful for story ideas, public policy, or
          regeneration planning.
        </p>
      </section>

      <Dialog open={successOpen} onOpenChange={setSuccessOpen}>
        <DialogContent>
          <DialogHeader>
            <p className="text-[0.7rem] uppercase tracking-[0.18em] text-signal">
              Newsletter
            </p>
            <DialogTitle className="mt-2">You are subscribed</DialogTitle>
            <DialogDescription className="mt-3">
              Subscription confirmed for{" "}
              <span className="font-medium text-foreground">
                {email.trim() || "your email"}
              </span>
              . You will get updates when trend, risk, or impact changes in the
              territory you selected.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              type="button"
              variant="accent"
              onClick={() => setSuccessOpen(false)}
            >
              Continue
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
