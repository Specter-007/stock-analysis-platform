import type { NextRequest } from "next/server";
import { proxyToBackend } from "@/lib/backend-proxy";

// Catch-all same-origin proxy for every /api/* request - see
// lib/backend-proxy.ts for why this replaced next.config.ts's rewrites().
// One reusable handler for every route/method rather than a fragile
// per-endpoint reimplementation.

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
