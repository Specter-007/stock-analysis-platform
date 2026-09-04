"use client";

import { useState } from "react";
import Link from "next/link";
import { KeyRound, Loader2 } from "lucide-react";
import { requestPasswordReset, ApiError } from "@/lib/api";
import { Card } from "@/components/ui/Card";

export default function ForgotPasswordPageClient() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await requestPasswordReset(email);
      setMessage(res.message);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-md px-4 sm:px-6 py-16">
      <div className="mb-6 text-center">
        <h1 className="text-xl font-semibold text-text-primary flex items-center justify-center gap-2">
          <KeyRound size={20} className="text-accent" aria-hidden="true" />
          Reset your password
        </h1>
      </div>

      <Card>
        {message ? (
          <p className="text-sm text-text-secondary">{message}</p>
        ) : (
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
              Send reset link
            </button>
          </form>
        )}
        <p className="text-xs text-text-muted text-center mt-4">
          <Link href="/login" className="text-accent hover:underline">Back to sign in</Link>
        </p>
      </Card>
    </div>
  );
}
