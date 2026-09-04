import { NextRequest, NextResponse } from "next/server";

// Server-only (never NEXT_PUBLIC_*) - the real backend URL. Read at
// request time, never sent to the browser. Used identically in local dev
// (defaults to the local backend) and production (the real Render URL,
// set via this exact env var in Vercel) - see lib/api.ts for why the
// browser always calls this app's own origin instead of ever knowing
// this value.
const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

// Headers that must never be forwarded verbatim in either direction -
// either because they describe the hop itself (host, content-length,
// connection) rather than the payload, or because a stale/incorrect
// value would corrupt the response (a mismatched content-length or a
// content-encoding claiming compression that was already decoded by
// fetch() causes the browser to fail to parse the body at all).
const REQUEST_HOP_BY_HOP_HEADERS = new Set(["host", "content-length", "connection"]);
const RESPONSE_HOP_BY_HOP_HEADERS = new Set([
  "content-encoding",
  "content-length",
  "transfer-encoding",
  "connection",
]);

/**
 * Same-origin API proxy: the browser only ever talks to this Next.js
 * app's own origin - this forwards the request server-side to the real
 * backend and forwards the response back in both directions.
 *
 * This exists instead of next.config.ts's declarative `rewrites()`
 * because that mechanism silently broke authentication in production:
 * rewrites to an external destination are handled by Vercel's own
 * routing layer, which is opaque and was not reliably forwarding the
 * `Cookie` request header and/or the backend's `Set-Cookie` response
 * headers - it worked against a local `next start` (a different internal
 * code path than Vercel's production edge routing for external rewrite
 * destinations) but not in real production. This handler forwards both
 * directions explicitly, under this app's own control.
 *
 * Three things that matter here, each a real production incident:
 * 1. A response can carry MULTIPLE Set-Cookie headers (login sets two -
 *    session_token and csrf_token). `Headers.get("set-cookie")` merges
 *    multiple values into a single comma-joined string, which is not
 *    valid Set-Cookie syntax and silently breaks one or both cookies -
 *    this uses `Headers.getSetCookie()` and re-appends each individually.
 * 2. Every proxied response gets an explicit `Cache-Control: no-store` -
 *    this is a personalized, cookie-authenticated API; if any layer
 *    (Vercel's edge, an intermediate CDN, the browser's own HTTP cache)
 *    ever cached a response here without this header, a stale
 *    unauthenticated 401 could keep being served to a now-authenticated
 *    user. Neither Next.js's own dynamic-route detection nor the backend
 *    omitting Cache-Control is a substitute for this being explicit here.
 * 3. This proxy is only ever reached at all if the browser calls this
 *    app's own origin in the first place - see lib/api.ts's API_BASE_URL,
 *    hardcoded to "" rather than read from an environment variable, after
 *    a real incident where a misconfigured NEXT_PUBLIC_API_BASE_URL made
 *    the deployed browser bundle call the backend directly, bypassing
 *    this proxy entirely regardless of how correct it was.
 */
export async function proxyToBackend(req: NextRequest, pathSegments: string[]): Promise<NextResponse> {
  const backendUrl = new URL(`/api/${pathSegments.join("/")}`, BACKEND_URL);
  backendUrl.search = req.nextUrl.search;

  const forwardHeaders = new Headers();
  req.headers.forEach((value, key) => {
    if (!REQUEST_HOP_BY_HOP_HEADERS.has(key.toLowerCase())) {
      forwardHeaders.append(key, value);
    }
  });

  const hasBody = !["GET", "HEAD"].includes(req.method);

  let backendResponse: Response;
  try {
    backendResponse = await fetch(backendUrl.toString(), {
      method: req.method,
      headers: forwardHeaders,
      body: hasBody ? await req.arrayBuffer() : undefined,
      redirect: "manual",
      // @ts-expect-error - Node's fetch requires this for a request with a body.
      duplex: hasBody ? "half" : undefined,
    });
  } catch (err) {
    // The backend itself was unreachable (not a backend-returned error
    // status) - return a real JSON error instead of letting this throw
    // into Next.js's generic HTML error page, which the frontend's
    // apiFetch (expects JSON) cannot parse into a useful message.
    console.error("[backend-proxy] upstream fetch failed", err instanceof Error ? err.message : err);
    const res = NextResponse.json(
      { error_type: "PROXY_UPSTREAM_UNREACHABLE", detail: "Could not reach the backend." },
      { status: 502 }
    );
    res.headers.set("cache-control", "no-store");
    return res;
  }

  const responseHeaders = new Headers();
  backendResponse.headers.forEach((value, key) => {
    if (!RESPONSE_HOP_BY_HOP_HEADERS.has(key.toLowerCase()) && key.toLowerCase() !== "set-cookie") {
      responseHeaders.append(key, value);
    }
  });
  for (const cookie of backendResponse.headers.getSetCookie()) {
    responseHeaders.append("set-cookie", cookie);
  }
  responseHeaders.set("cache-control", "no-store");

  return new NextResponse(backendResponse.body, {
    status: backendResponse.status,
    statusText: backendResponse.statusText,
    headers: responseHeaders,
  });
}
