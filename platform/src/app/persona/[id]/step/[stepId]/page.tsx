import { redirect } from "next/navigation";

/** Legacy prototype route — product surface is Explore + Newsletter. */
export default function PersonaStepPage() {
  redirect("/explore");
}
