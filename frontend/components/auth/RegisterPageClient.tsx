"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { UserPlus, Loader2 } from "lucide-react";
import { registerAccount, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Card } from "@/components/ui/Card";

export default function RegisterPageClient() {
  const router = useRouter();
  const { refresh } = useAuth();

  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [acceptTerms, setAcceptTerms] = useState(false);
  const [marketingConsent, setMarketingConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await registerAccount({
        email,
        password,
        display_name: displayName,
        accept_terms: acceptTerms,
        marketing_consent: marketingConsent,
      });
      await refresh();
      router.push("/onboarding");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Registration failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-md px-4 sm:px-6 py-16">
      <div className="mb-6 text-center">
        <h1 className="text-xl font-semibold text-text-primary flex items-center justify-center gap-2">
          <UserPlus size={20} className="text-accent" aria-hidden="true" />
          Create an account
        </h1>
        <p className="text-sm text-text-muted mt-1">Free. Research-only - no broker connection, ever.</p>
      </div>

      <Card>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
          <label className="flex flex-col gap-1.5 text-xs">
            <span className="text-text-muted font-medium">Display name</span>
            <input
              required
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary"
            />
          </label>

          <label className="flex flex-col gap-1.5 text-xs">
            <span className="text-text-muted font-medium">Email</span>
            <input
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary"
            />
          </label>

          <label className="flex flex-col gap-1.5 text-xs">
            <span className="text-text-muted font-medium">Password</span>
            <input
              type="password"
              required
              minLength={8}
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary"
            />
            <span className="text-text-faint">At least 8 characters, with a letter and a number.</span>
          </label>

          <label className="flex items-start gap-2 text-xs text-text-secondary">
            <input
              type="checkbox"
              required
              checked={acceptTerms}
              onChange={(e) => setAcceptTerms(e.target.checked)}
              className="mt-0.5"
            />
            <span>
              I have read and accept the{" "}
              <Link href="/terms" className="text-accent hover:underline">Terms of Service</Link> and{" "}
              <Link href="/privacy" className="text-accent hover:underline">Privacy Policy</Link>.
            </span>
          </label>

          <label className="flex items-start gap-2 text-xs text-text-secondary">
            <input
              type="checkbox"
              checked={marketingConsent}
              onChange={(e) => setMarketingConsent(e.target.checked)}
              className="mt-0.5"
            />
            <span>Send me occasional product updates (optional - separate from the Terms above).</span>
          </label>

          {error && (
            <p role="alert" className="text-xs text-bearish bg-bearish-dim rounded-md px-3 py-2">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={busy || !acceptTerms}
            className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-accent text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 cursor-pointer"
          >
            {busy && <Loader2 size={16} className="animate-spin" aria-hidden="true" />}
            Create account
          </button>

          <p className="text-xs text-text-muted text-center">
            Already have an account?{" "}
            <Link href="/login" className="text-accent hover:underline">Sign in</Link>
          </p>
        </form>
      </Card>
    </div>
  );
}
