"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  STORAGE_KEY,
  defaultPreferences,
  normalizePreferences,
  type AlertPreferences,
  type UserProfile,
} from "@/data/alerts";

export type StakeholderRole = UserProfile["role"];

export type NewsletterSubscription = {
  email: string;
  role: StakeholderRole;
  org?: string;
  preferences: AlertPreferences;
};

type NewsletterContextValue = {
  subscription: NewsletterSubscription | null;
  ready: boolean;
  subscribe: (input: {
    email: string;
    role: StakeholderRole;
    org?: string;
    preferences: AlertPreferences;
  }) => void;
  updatePreferences: (preferences: AlertPreferences) => void;
  unsubscribe: () => void;
};

const NewsletterContext = createContext<NewsletterContextValue | null>(null);

function readStored(): NewsletterSubscription | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<UserProfile> &
      Partial<NewsletterSubscription>;
    if (!parsed.email) return null;
    return {
      email: String(parsed.email).trim().toLowerCase(),
      role: (parsed.role as StakeholderRole) || "gestor",
      org: parsed.org?.trim() || undefined,
      preferences: normalizePreferences(parsed.preferences),
    };
  } catch {
    return null;
  }
}

function writeStored(sub: NewsletterSubscription | null) {
  if (typeof window === "undefined") return;
  if (!sub) {
    localStorage.removeItem(STORAGE_KEY);
    return;
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(sub));
}

export function NewsletterProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [subscription, setSubscription] =
    useState<NewsletterSubscription | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setSubscription(readStored());
    setReady(true);
  }, []);

  const subscribe = useCallback(
    (input: {
      email: string;
      role: StakeholderRole;
      org?: string;
      preferences: AlertPreferences;
    }) => {
      const next: NewsletterSubscription = {
        email: input.email.trim().toLowerCase(),
        role: input.role,
        org: input.org?.trim() || undefined,
        preferences: normalizePreferences({
          ...input.preferences,
          alertsEnabled: true,
        }),
      };
      writeStored(next);
      setSubscription(next);
    },
    []
  );

  const updatePreferences = useCallback((preferences: AlertPreferences) => {
    setSubscription((prev) => {
      if (!prev) return prev;
      const next = {
        ...prev,
        preferences: normalizePreferences(preferences),
      };
      writeStored(next);
      return next;
    });
  }, []);

  const unsubscribe = useCallback(() => {
    setSubscription((prev) => {
      if (!prev) return prev;
      const next = {
        ...prev,
        preferences: normalizePreferences({
          ...prev.preferences,
          alertsEnabled: false,
        }),
      };
      writeStored(next);
      return next;
    });
  }, []);

  const value = useMemo(
    () => ({
      subscription,
      ready,
      subscribe,
      updatePreferences,
      unsubscribe,
    }),
    [subscription, ready, subscribe, updatePreferences, unsubscribe]
  );

  return (
    <NewsletterContext.Provider value={value}>
      {children}
    </NewsletterContext.Provider>
  );
}

export function useNewsletter() {
  const ctx = useContext(NewsletterContext);
  if (!ctx) {
    throw new Error("useNewsletter must be used within NewsletterProvider");
  }
  return ctx;
}

export { defaultPreferences };
