import { redirect } from "next/navigation";

/** Preferências e newsletter vivem em /newsletter. */
export default function PreferenciasPage() {
  redirect("/newsletter");
}
