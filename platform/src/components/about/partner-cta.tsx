"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";

/** Company-only partner interest — stays on About, no newsletter redirect. */
export function PartnerCta() {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [org, setOrg] = useState("");
  const [sent, setSent] = useState(false);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim() || !email.includes("@")) return;
    setSent(true);
  }

  if (sent) {
    return (
      <p className="max-w-sm text-sm leading-relaxed text-olive">
        Thanks — we registered your partner interest for{" "}
        <strong>{org.trim() || email}</strong>. This prototype stores nothing on
        a server; in production this would reach the partnerships desk.
      </p>
    );
  }

  if (!open) {
    return (
      <Button
        type="button"
        size="lg"
        variant="accent"
        onClick={() => setOpen(true)}
      >
        Become a partner
      </Button>
    );
  }

  return (
    <form
      id="partner-form"
      onSubmit={handleSubmit}
      className="w-full max-w-sm space-y-3"
    >
      <label className="block text-sm">
        <span className="mb-1 block text-xs uppercase tracking-[0.12em] text-muted-foreground">
          Work email
        </span>
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="name@company.com"
          className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
        />
      </label>
      <label className="block text-sm">
        <span className="mb-1 block text-xs uppercase tracking-[0.12em] text-muted-foreground">
          Company
        </span>
        <input
          value={org}
          onChange={(e) => setOrg(e.target.value)}
          placeholder="Organization"
          className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
        />
      </label>
      <div className="flex flex-wrap gap-2">
        <Button type="submit" size="sm" variant="accent">
          Send partner interest
        </Button>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          onClick={() => setOpen(false)}
        >
          Cancel
        </Button>
      </div>
    </form>
  );
}
