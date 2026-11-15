import type { Metadata } from "next";
import { TheTeam } from "@/components/team/the-team";

export const metadata: Metadata = {
  title: "The Team",
  description:
    "Who builds Climate Sentinel — design, geospatial intelligence, software, and delivery.",
};

export default function TeamPage() {
  return <TheTeam />;
}
