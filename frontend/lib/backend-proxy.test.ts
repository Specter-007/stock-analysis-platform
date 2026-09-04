import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { proxyToBackend } from "@/lib/backend-proxy";

// Regression coverage for the real production bug: login returned 200 but
// /api/auth/me returned 401 because next.config.ts's rewrites() (Vercel's
// opaque external-rewrite routing) did not reliably forward the Cookie
// request header and/or the backend's Set-Cookie response headers. This
// tests the replacement - a Next.js Route Handler this app fully
// controls - by mocking the backend fetch call directly, so these
// assertions exercise the exact forwarding logic without needing a real
// backend or a real Vercel deployment.

describe("proxyToBackend", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("forwards multiple Set-Cookie response headers as separate cookies, not merged", async () => {
    const mockResponse = new Response(JSON.stringify({ ok: true }), {
      status: 201,
      headers: [
        ["set-cookie", "session_token=abc123; HttpOnly; Path=/; SameSite=lax"],
        ["set-cookie", "csrf_token=xyz789; Path=/; SameSite=lax"],
        ["content-type", "application/json"],
      ],
    });
    const fetchMock = vi.fn().mockResolvedValue(mockResponse);
    vi.stubGlobal("fetch", fetchMock);

    const req = new NextRequest("http://frontend.example/api/auth/register", { method: "POST" });
    const res = await proxyToBackend(req, ["auth", "register"]);

    const cookies = res.headers.getSetCookie();
    expect(cookies).toHaveLength(2);
    expect(cookies).toContain("session_token=abc123; HttpOnly; Path=/; SameSite=lax");
    expect(cookies).toContain("csrf_token=xyz789; Path=/; SameSite=lax");
    expect(res.status).toBe(201);
  });

  it("forwards the incoming Cookie header to the backend", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const req = new NextRequest("http://frontend.example/api/auth/me", {
      headers: { cookie: "session_token=abc123; csrf_token=xyz789" },
    });
    await proxyToBackend(req, ["auth", "me"]);

    const forwardedHeaders = fetchMock.mock.calls[0][1].headers as Headers;
    expect(forwardedHeaders.get("cookie")).toBe("session_token=abc123; csrf_token=xyz789");
  });

  it("forwards the request method, body, and a custom header (e.g. X-CSRF-Token) to the backend", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const req = new NextRequest("http://frontend.example/api/watchlist", {
      method: "POST",
      headers: { "content-type": "application/json", "x-csrf-token": "xyz789" },
      body: JSON.stringify({ ticker: "AAPL" }),
    });
    await proxyToBackend(req, ["watchlist"]);

    const [calledUrl, calledInit] = fetchMock.mock.calls[0];
    expect(calledUrl).toBe("http://localhost:8000/api/watchlist");
    expect(calledInit.method).toBe("POST");
    expect((calledInit.headers as Headers).get("x-csrf-token")).toBe("xyz789");
    expect(new TextDecoder().decode(calledInit.body as ArrayBuffer)).toBe(JSON.stringify({ ticker: "AAPL" }));
  });

  it("does not attach a body for a GET request", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const req = new NextRequest("http://frontend.example/api/auth/me");
    await proxyToBackend(req, ["auth", "me"]);

    const calledInit = fetchMock.mock.calls[0][1];
    expect(calledInit.body).toBeUndefined();
  });

  it("passes through the backend's status code and JSON body unchanged", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "Not authenticated" }), {
        status: 401,
        headers: { "content-type": "application/json" },
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    const req = new NextRequest("http://frontend.example/api/auth/me");
    const res = await proxyToBackend(req, ["auth", "me"]);

    expect(res.status).toBe(401);
    const body = await res.json();
    expect(body).toEqual({ detail: "Not authenticated" });
  });

  it("strips hop-by-hop headers (host) from the outgoing request", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const req = new NextRequest("http://frontend.example/api/auth/me", {
      headers: { host: "stock-analysis-platform-gamma.vercel.app" },
    });
    await proxyToBackend(req, ["auth", "me"]);

    const forwardedHeaders = fetchMock.mock.calls[0][1].headers as Headers;
    expect(forwardedHeaders.has("host")).toBe(false);
  });

  it("always sets Cache-Control: no-store on the proxied response", async () => {
    // This is a personalized, cookie-authenticated API proxy - if any layer
    // (Vercel's edge, an intermediate CDN, the browser's own cache) ever
    // cached a response here, a stale unauthenticated 401 could keep being
    // served to a now-authenticated user. Explicit regardless of whether
    // any specific caching layer is confirmed to be the production cause.
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const req = new NextRequest("http://frontend.example/api/auth/me");
    const res = await proxyToBackend(req, ["auth", "me"]);

    expect(res.headers.get("cache-control")).toBe("no-store");
  });

  it("exposes safe (non-sensitive) debug headers describing cookie flow", async () => {
    const mockResponse = new Response("{}", {
      status: 200,
      headers: [
        ["set-cookie", "session_token=abc123; HttpOnly; Path=/; SameSite=lax"],
        ["set-cookie", "csrf_token=xyz789; Path=/; SameSite=lax"],
      ],
    });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(mockResponse));

    const req = new NextRequest("http://frontend.example/api/auth/me", {
      headers: { cookie: "session_token=abc123; csrf_token=xyz789" },
    });
    const res = await proxyToBackend(req, ["auth", "me"]);

    expect(res.headers.get("x-debug-cookie-received")).toBe("true");
    expect(res.headers.get("x-debug-cookie-names")).toBe("session_token,csrf_token");
    expect(res.headers.get("x-debug-backend-status")).toBe("200");
    expect(res.headers.get("x-debug-setcookie-count")).toBe("2");
    expect(res.headers.get("x-debug-setcookie-names")).toBe("session_token,csrf_token");

    // The debug headers specifically must only ever carry cookie NAMES,
    // never values - unlike the real `set-cookie` header (which correctly
    // does carry the real value; that's how cookies work), a debug header
    // leaking a token value would defeat the entire point of it being safe
    // to look at in devtools.
    for (const [key, value] of res.headers) {
      if (key.toLowerCase().startsWith("x-debug-")) {
        expect(value).not.toContain("abc123");
        expect(value).not.toContain("xyz789");
      }
    }
  });

  it("reports no cookie received (not a crash) when the request has none", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 401 })));

    const req = new NextRequest("http://frontend.example/api/auth/me");
    const res = await proxyToBackend(req, ["auth", "me"]);

    expect(res.headers.get("x-debug-cookie-received")).toBe("false");
    expect(res.headers.get("x-debug-cookie-names")).toBe("(none)");
  });

  it("returns a real JSON 502 (not an unhandled exception) if the backend is unreachable", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new Error("ECONNREFUSED"))
    );
    vi.spyOn(console, "error").mockImplementation(() => {});

    const req = new NextRequest("http://frontend.example/api/auth/me");
    const res = await proxyToBackend(req, ["auth", "me"]);

    expect(res.status).toBe(502);
    const body = await res.json();
    expect(body.error_type).toBe("PROXY_UPSTREAM_UNREACHABLE");
    expect(res.headers.get("cache-control")).toBe("no-store");
  });
});
