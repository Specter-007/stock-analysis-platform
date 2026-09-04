import { afterEach, describe, expect, it, vi } from "vitest";

// Regression test for a real production incident: the browser was
// observed (Chrome DevTools) calling https://stock-analyst-backend.onrender.com/api/auth/login
// DIRECTLY instead of this app's own same-origin /api/auth/login - login
// appeared to succeed, but the session cookie could never come back
// (SameSite=Lax is never sent on a genuine cross-site fetch), so every
// subsequent page still showed "Sign In". Root cause: API_BASE_URL used
// to be read from NEXT_PUBLIC_API_BASE_URL, a build-time environment
// variable baked into the browser bundle - if that value was ever wrong,
// stale, or not actually saved as an empty string in the hosting
// dashboard, the browser silently called the backend directly, bypassing
// the same-origin proxy (app/api/[...path]/route.ts) entirely, no matter
// how correct that proxy itself was.
//
// Fixed by removing the environment variable from this code path
// entirely - API_BASE_URL is now a hardcoded empty string, not
// configurable. These tests prove there is no longer any environment
// variable value that can change that.
describe("API_BASE_URL", () => {
  const ORIGINAL_ENV = process.env.NEXT_PUBLIC_API_BASE_URL;

  afterEach(() => {
    if (ORIGINAL_ENV === undefined) delete process.env.NEXT_PUBLIC_API_BASE_URL;
    else process.env.NEXT_PUBLIC_API_BASE_URL = ORIGINAL_ENV;
    vi.resetModules();
  });

  it("is always an empty string (same-origin), regardless of any environment variable", async () => {
    vi.resetModules();
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
    const { API_BASE_URL } = await import("@/lib/api");
    expect(API_BASE_URL).toBe("");
  });

  it("cannot be overridden by NEXT_PUBLIC_API_BASE_URL pointing at a real backend URL - the exact misconfiguration that caused a real incident", async () => {
    vi.resetModules();
    process.env.NEXT_PUBLIC_API_BASE_URL = "https://stock-analyst-backend.onrender.com";
    const { API_BASE_URL } = await import("@/lib/api");
    expect(API_BASE_URL).toBe("");
  });

  it("cannot be overridden even by an unrelated non-empty value", async () => {
    vi.resetModules();
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:9999";
    const { API_BASE_URL } = await import("@/lib/api");
    expect(API_BASE_URL).toBe("");
  });
});
