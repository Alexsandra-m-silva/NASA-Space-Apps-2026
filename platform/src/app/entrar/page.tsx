import { redirect } from "next/navigation";

/** Rota legada — a newsletter vive em /newsletter. */
export default function EntrarPage() {
  redirect("/newsletter");
}
