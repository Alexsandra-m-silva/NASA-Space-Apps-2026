import { redirect } from "next/navigation";

/** Legacy Portuguese route — Explore now lives at /explore. */
export default function ExplorarRedirectPage() {
  redirect("/explore");
}
