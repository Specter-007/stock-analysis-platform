"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { MailCheck, Loader2, XCircle } from "lucide-react";
import { confirmEmailVerification, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Card } from "@/components/ui/Card";

export default function VerifyEmailPageClient() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";
  const { refresh } = useAuth();

  const [status, setStatus] = useState<"pending" | "done" | "error">(token ? "pending" : "error");
  const [error, setError] = useState<string | null>(token ? null : "No verification token found in this link.");

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    confirmEmailVerification(token)
      .then(async () => {
        await refresh();
        if (!cancelled) setStatus("done");
      })
      .catch((err) => {
        if (cancelled) return;
        setStatus("error");
        setError(err instanceof ApiError ? err.message : "This link is invalid or has expired.");
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  return (
    <div className="mx-auto max-w-md px-4 sm:px-6 py-16">
      <Card>
        {status === "pending" && (
          <div className="flex items-center gap-2 text-sm text-text-muted">
            <Loader2 size={16} className="animate-spin" aria-hidden="true" /> Verifying...
          </div>
        )}
        {status === "done" && (
          <div className="flex flex-col items-center gap-2 text-center">
            <MailCheck size={24} className="text-bullish" aria-hidden="true" />
            <p className="text-sm text-text-secondary">Your email address is verified.</p>
            <Link href="/" className="text-accent hover:underline text-sm">Go to the dashboard</Link>
          </div>
        )}
        {status === "error" && (
          <div className="flex flex-col items-center gap-2 text-center">
            <XCircle size={24} className="text-bearish" aria-hidden="true" />
            <p className="text-sm text-bearish">{error}</p>
            <Link href="/settings/account" className="text-accent hover:underline text-sm">
              Request a new link from Account Settings
            </Link>
          </div>
        )}
      </Card>
    </div>
  );
}
