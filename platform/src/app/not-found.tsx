import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="mx-auto flex min-h-[60vh] max-w-lg flex-col items-start justify-center px-4 py-16">
      <h1 className="font-display text-3xl text-olive">Page not found</h1>
      <p className="mt-3 text-sm text-muted-foreground">
        That route is not part of Climate Sentinel.
      </p>
      <Button asChild className="mt-6">
        <Link href="/">Back to About</Link>
      </Button>
    </div>
  );
}
