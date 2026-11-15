import type { Metadata } from "next";
import { AboutLanding } from "@/components/about/about-landing";

export const metadata: Metadata = {
  title: "About",
  description:
    "Climate Sentinel — from surface trends to the cost of inaction, and regeneration that earns credits.",
};

export default function AboutPage() {
  return <AboutLanding />;
}
