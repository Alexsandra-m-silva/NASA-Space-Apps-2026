import type { Metadata } from "next";
import { LearnGame } from "@/components/learn-game/learn-game";

export const metadata: Metadata = {
  title: "Learn by playing",
  description:
    "Explore a 3D Caatinga landscape in WebXR and learn how satellite evidence, local partnerships, and native plants support restoration.",
};

export default function LearnByPlayingPage() {
  return <LearnGame />;
}
