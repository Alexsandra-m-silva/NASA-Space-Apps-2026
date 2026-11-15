import type { NextConfig } from "next";

// In Docker/Easypanel the nginx in front of the platform serves /api, /municipios
// and /products. Running the platform alone (npm run build/start), set
// DEV_PROXY=https://<deployed host> at build time to proxy those paths there.
const devProxy = process.env.DEV_PROXY?.replace(/\/$/, "");

const nextConfig: NextConfig = {
  // Dev server binds as localhost; computerUse / curl often use 127.0.0.1.
  // Without this, Next blocks cross-origin /_next assets and client hydration stalls.
  allowedDevOrigins: ["127.0.0.1"],
  async rewrites() {
    if (!devProxy) return [];
    return ["api", "municipios", "products"].map((p) => ({
      source: `/${p}/:path*`,
      destination: `${devProxy}/${p}/:path*`,
    }));
  },
};

export default nextConfig;
