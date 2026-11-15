import { Suspense } from "react";
import { AtualizacoesWorkspace } from "@/components/auth/atualizacoes-workspace";
import { EmailTriggersCard } from "@/components/auth/email-triggers-card";

export const metadata = {
  title: "Newsletter",
  description:
    "Email newsletter on desertification risk, impact, and surface trends — for press, government, and business.",
};

function NewsletterFallback() {
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
        <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
          Preparing your signup…
        </p>
      </div>
      <EmailTriggersCard />
    </div>
  );
}

export default function NewsletterPage() {
  return (
    <Suspense fallback={<NewsletterFallback />}>
      <AtualizacoesWorkspace />
    </Suspense>
  );
}
