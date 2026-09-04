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
});
