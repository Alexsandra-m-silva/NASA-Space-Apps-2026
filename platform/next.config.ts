import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Dev server binds as localhost; computerUse / curl often use 127.0.0.1.
  // Without this, Next blocks cross-origin /_next assets and client hydration stalls.
  allowedDevOrigins: ["127.0.0.1"],
};

export default nextConfig;
