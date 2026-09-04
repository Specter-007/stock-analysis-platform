import { afterEach, describe, expect, it, vi } from "vitest";

// Regression test for the production auth bug: login returned 200 but
// /api/auth/me returned 401. Root cause was that `||` treats an
// intentionally-empty NEXT_PUBLIC_API_BASE_URL (production's same-origin
// proxy mode - see next.config.ts's rewrites()) as falsy and silently
// falls back to "http://localhost:8000", which made the deployed frontend
// call a *cross-site* backend directly instead of routing through the
// same-origin proxy - and a SameSite=Lax session/CSRF cookie is never
// attached to a genuine cross-site fetch. Fixed by switching to `??`,
// which only falls back on a genuinely unset (undefined) value.
describe("API_BASE_URL", () => {
  const ORIGINAL_ENV = process.env.NEXT_PUBLIC_API_BASE_URL;

  afterEach(() => {
    if (ORIGINAL_ENV === undefined) delete process.env.NEXT_PUBLIC_API_BASE_URL;
    else process.env.NEXT_PUBLIC_API_BASE_URL = ORIGINAL_ENV;
    vi.resetModules();
  });

  it("keeps an explicitly-empty value as empty (same-origin proxy mode), not falling back to localhost", async () => {
    vi.resetModules();
    process.env.NEXT_PUBLIC_API_BASE_URL = "";
    const { API_BASE_URL } = await import("@/lib/api");
    expect(API_BASE_URL).toBe("");
  });

  it("falls back to localhost:8000 only when genuinely unset", async () => {
    vi.resetModules();
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
    const { API_BASE_URL } = await import("@/lib/api");
    expect(API_BASE_URL).toBe("http://localhost:8000");
  });

  it("uses an explicit non-empty value verbatim when set", async () => {
    vi.resetModules();
    process.env.NEXT_PUBLIC_API_BASE_URL = "https://example.onrender.com";
    const { API_BASE_URL } = await import("@/lib/api");
    expect(API_BASE_URL).toBe("https://example.onrender.com");
  });
});
