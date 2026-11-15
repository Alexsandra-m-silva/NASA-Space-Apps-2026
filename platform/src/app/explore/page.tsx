import { Suspense } from "react";
import { ExploreWorkspace } from "@/components/explore/explore-workspace";

export const metadata = {
  title: "Explore",
  description:
    "Heat map, rankings by trend, risk, impact and carbon, and cost of inaction.",
};

export default function ExplorePage() {
  return (
    <div className="mx-auto max-w-6xl px-4 pb-20 pt-8 sm:px-6 sm:pt-10">
      <Suspense
        fallback={
          <p className="text-sm text-muted-foreground">Loading explore…</p>
        }
      >
        <ExploreWorkspace />
      </Suspense>
    </div>
  );
}
