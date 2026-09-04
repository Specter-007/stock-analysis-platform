import { NextRequest, NextResponse } from "next/server";

// Server-only (never NEXT_PUBLIC_*) - the real backend URL. Read at
// request time, never sent to the browser. Not used in local dev, where
// the frontend calls the local backend directly via
// NEXT_PUBLIC_API_BASE_URL instead (see frontend/.env.local).
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
 * backend and forwards the response back, byte-for-byte, in both
 * directions.
 *
 * This exists instead of next.config.ts's declarative `rewrites()`
 * because that mechanism silently broke authentication in production:
 * rewrites to an external destination are handled by Vercel's own
 * routing layer, which is opaque and was not reliably forwarding the
 * `Cookie` request header and/or the backend's `Set-Cookie` response
 * headers - it worked against a local `next start` (which uses a
 * different internal code path than Vercel's production edge routing for
 * external rewrite destinations) but not in real production. This
 * handler forwards both directions explicitly, under this app's own
 * control, so it can be verified rather than trusted.
 *
 * The one subtlety that actually matters: a response can carry MULTIPLE
 * Set-Cookie headers (this app's login sets two - session_token and
 * csrf_token). `Headers.get("set-cookie")` merges multiple values into a
 * single comma-joined string, which is not valid Set-Cookie syntax and
 * silently breaks one or both cookies - this must use
 * `Headers.getSetCookie()` and re-append each cookie individually.
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

  const backendResponse = await fetch(backendUrl.toString(), {
    method: req.method,
    headers: forwardHeaders,
    body: hasBody ? await req.arrayBuffer() : undefined,
    redirect: "manual",
    // @ts-expect-error - Node's fetch requires this for a request with a body.
    duplex: hasBody ? "half" : undefined,
  });

  const responseHeaders = new Headers();
  backendResponse.headers.forEach((value, key) => {
    if (!RESPONSE_HOP_BY_HOP_HEADERS.has(key.toLowerCase()) && key.toLowerCase() !== "set-cookie") {
      responseHeaders.append(key, value);
    }
  });
  for (const cookie of backendResponse.headers.getSetCookie()) {
    responseHeaders.append("set-cookie", cookie);
  }

  return new NextResponse(backendResponse.body, {
    status: backendResponse.status,
    statusText: backendResponse.statusText,
    headers: responseHeaders,
  });
}
