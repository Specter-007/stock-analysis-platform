import type { NextConfig } from "next";

// The /api/* same-origin backend proxy lives at app/api/[...path]/route.ts,
// not here. An earlier version of this file used rewrites() for that, but
// rewrites to an external destination are handled by Vercel's own opaque
// routing layer, which did not reliably forward the Cookie request header
// and the backend's (multiple) Set-Cookie response headers in real
// production - see lib/backend-proxy.ts for the full explanation and
// docs/DEPLOYMENT.md for the incident. A Next.js Route Handler is this
// app's own code, fully under its control and verifiable, instead of a
// black box.
const nextConfig: NextConfig = {};

export default nextConfig;
