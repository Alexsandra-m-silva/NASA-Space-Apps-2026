import Link from "next/link";
import { Button } from "@/components/ui/button";

export const metadata = {
  title: "Download",
  description: "Download the Climate Sentinel project zip.",
};

export default function DownloadPage() {
  return (
    <div
      data-header-contrast="light"
      className="mx-auto flex min-h-[70vh] max-w-xl flex-col justify-center px-4 py-16 sm:px-6"
    >
      <p className="text-[0.7rem] uppercase tracking-[0.18em] text-signal">
        Project pack
      </p>
      <h1 className="mt-2 font-display text-3xl text-olive sm:text-4xl">
        Download Climate Sentinel
      </h1>
      <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
        Full prototype source for Explore and Newsletter (without{" "}
        <code className="text-xs">node_modules</code>). After unzipping, run{" "}
        <code className="text-xs">npm install</code> then{" "}
        <code className="text-xs">npm run dev</code>.
      </p>
      <div className="mt-8 flex flex-wrap gap-3">
        <Button asChild size="lg">
          <a
            href="/Desert-Sentinel-explore-newsletter.zip"
            download="Desert-Sentinel-explore-newsletter.zip"
          >
            Download ZIP
          </a>
        </Button>
        <Button asChild size="lg" variant="outline">
          <Link href="/explore">Open Explore</Link>
        </Button>
      </div>
      <p className="mt-6 text-xs text-muted-foreground">
        Direct file:{" "}
        <a
          className="underline underline-offset-2 hover:text-foreground"
          href="/Desert-Sentinel-explore-newsletter.zip"
          download
        >
          /Desert-Sentinel-explore-newsletter.zip
        </a>
      </p>
    </div>
  );
}
