import type { NextConfig } from "next";

// Server-only (never NEXT_PUBLIC_*) - the real backend URL, read at
// request time by Vercel's routing layer, never sent to the browser. Not
// used in local dev, where the frontend calls the local backend directly
// via NEXT_PUBLIC_API_BASE_URL instead (see frontend/.env.local).
const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    // Same-origin API proxy: the browser only ever talks to this Next.js
    // app's own origin (/api/*), which Vercel forwards server-side to the
    // real backend. This is the fix for auth in production, not a
    // convenience - the frontend and backend are on different registrable
    // domains (vercel.app / onrender.com), and a SameSite=Lax session/CSRF
    // cookie is never attached to a genuine cross-site fetch. Routing
    // through this proxy makes every request same-origin instead, so
    // SameSite=Lax, Secure, and HttpOnly all keep working exactly as
    // configured - no cookie/CORS security setting was loosened to fix
    // this. See docs/DEPLOYMENT.md.
    return [
      {
        source: "/api/:path*",
        destination: `${BACKEND_URL}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
