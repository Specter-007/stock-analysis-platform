"use client";

import { useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { KeyRound, Loader2 } from "lucide-react";
import { confirmPasswordReset, ApiError } from "@/lib/api";
import { Card } from "@/components/ui/Card";

export default function ResetPasswordPageClient() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";

  const [newPassword, setNewPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await confirmPasswordReset(token, newPassword);
      setDone(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "This link is invalid or has expired.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-md px-4 sm:px-6 py-16">
      <div className="mb-6 text-center">
        <h1 className="text-xl font-semibold text-text-primary flex items-center justify-center gap-2">
          <KeyRound size={20} className="text-accent" aria-hidden="true" />
          Choose a new password
        </h1>
      </div>

      <Card>
        {!token ? (
          <p className="text-sm text-bearish">No reset token found in this link. Request a new one.</p>
        ) : done ? (
          <p className="text-sm text-text-secondary">
            Password reset. <Link href="/login" className="text-accent hover:underline">Sign in</Link> with your new password.
          </p>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
            <label className="flex flex-col gap-1.5 text-xs">
              <span className="text-text-muted font-medium">New password</span>
              <input
                type="password"
                required
                minLength={8}
                autoComplete="new-password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
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
              Reset password
            </button>
          </form>
        )}
      </Card>
    </div>
  );
}
