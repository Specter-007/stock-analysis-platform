import type { NextRequest } from "next/server";
import { proxyToBackend } from "@/lib/backend-proxy";

// Catch-all same-origin proxy for every /api/* request - see
// lib/backend-proxy.ts for why this replaced next.config.ts's rewrites().
// One reusable handler for every route/method rather than a fragile
// per-endpoint reimplementation.
//
// Explicit, not left to default inference: this must run on the Node.js
// serverless runtime (not the Edge runtime) - Headers.getSetCookie(), used
// in lib/backend-proxy.ts to forward multiple Set-Cookie headers
// correctly, requires it. Also explicitly opted out of any static/ISR
// caching - this proxies live, per-user, cookie-authenticated requests.
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type RouteContext = { params: Promise<{ path: string[] }> };

async function handle(req: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxyToBackend(req, path);
}

export const GET = handle;
export const POST = handle;
export const PUT = handle;
export const PATCH = handle;
export const DELETE = handle;
export const OPTIONS = handle;
