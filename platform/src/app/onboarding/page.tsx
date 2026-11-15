import { redirect } from "next/navigation";

/** Onboarding legado — o fluxo é a newsletter em /newsletter. */
export default function OnboardingPage() {
  redirect("/newsletter");
}
