"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { LogIn, Loader2 } from "lucide-react";
import { login, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Card } from "@/components/ui/Card";

export default function LoginPageClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { refresh } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
      await refresh();
      const next = searchParams.get("next") || "/";
      router.push(next);
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        setError("Too many attempts. Please wait a moment and try again.");
      } else {
        setError(err instanceof ApiError ? err.message : "Sign in failed.");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-md px-4 sm:px-6 py-16">
      <div className="mb-6 text-center">
        <h1 className="text-xl font-semibold text-text-primary flex items-center justify-center gap-2">
          <LogIn size={20} className="text-accent" aria-hidden="true" />
          Sign in
        </h1>
        <p className="text-sm text-text-muted mt-1">Access your watchlists, paper portfolios, and experiments.</p>
      </div>

      <Card>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
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
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary"
            />
          </label>

          {error && (
            <p role="alert" className="text-xs text-bearish bg-bearish-dim rounded-md px-3 py-2">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={busy}
            className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-accent text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 cursor-pointer"
          >
            {busy && <Loader2 size={16} className="animate-spin" aria-hidden="true" />}
            Sign in
          </button>

          <div className="flex items-center justify-between text-xs">
            <Link href="/forgot-password" className="text-accent hover:underline">
              Forgot password?
            </Link>
            <Link href="/register" className="text-text-muted hover:text-text-primary">
              Create an account
            </Link>
          </div>
        </form>
      </Card>
    </div>
  );
}
