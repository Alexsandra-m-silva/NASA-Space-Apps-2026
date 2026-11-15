"use client";

import { useEffect, useRef } from "react";

/**
 * Background video for the About hero.
 *
 * The `autoPlay` attribute alone is not reliable after SSR + hydration: Chrome
 * may leave the element paused with only metadata loaded. Following the
 * Hefesto hero, we force `muted` on the element and call `play()` on mount;
 * if the browser still refuses, we retry on the first user interaction or
 * when the tab becomes visible.
 */
export function HeroVideo({ src, className }: { src: string; className?: string }) {
  const ref = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = ref.current;
    if (!video) return;
    video.muted = true;
    video.defaultMuted = true;
    video.playsInline = true;

    const tryPlay = () => {
      if (!video.paused) return;
      video.play().catch(() => {});
    };

    tryPlay();
    video.addEventListener("canplay", tryPlay);
    const events = ["scroll", "pointerdown", "keydown", "touchstart"] as const;
    events.forEach((e) => window.addEventListener(e, tryPlay, { passive: true }));
    const onVisible = () => {
      if (!document.hidden) tryPlay();
    };
    document.addEventListener("visibilitychange", onVisible);

    return () => {
      video.removeEventListener("canplay", tryPlay);
      events.forEach((e) => window.removeEventListener(e, tryPlay));
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, []);

  return (
    <video
      ref={ref}
      className={className}
      src={src}
      autoPlay
      muted
      loop
      playsInline
      preload="auto"
      aria-hidden
    />
  );
}
