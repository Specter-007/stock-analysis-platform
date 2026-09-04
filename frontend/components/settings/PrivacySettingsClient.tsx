"use client";

import { useEffect, useState } from "react";
import { Download, ShieldCheck } from "lucide-react";
import { getPreferences, getAccountExportUrl, ApiError } from "@/lib/api";
import type { Preferences } from "@/types/auth";
import { Card, CardHeader } from "@/components/ui/Card";

export function PrivacySettingsClient() {
  const [prefs, setPrefs] = useState<Preferences | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getPreferences()
      .then((res) => {
        if (!cancelled) setPrefs(res);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Could not load preferences.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader title="Your consent" subtitle="Recorded when you registered - see the Privacy Policy for what each means." />
        {error && <p className="text-xs text-bearish">{error}</p>}
        {prefs && (
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
            <dt className="text-text-muted">Terms of Service accepted</dt>
            <dd className="text-text-primary">
              {prefs.terms_accepted_at ? new Date(prefs.terms_accepted_at).toLocaleString() : "Not recorded"}
            </dd>
            <dt className="text-text-muted">Privacy Policy accepted</dt>
            <dd className="text-text-primary">
              {prefs.privacy_accepted_at ? new Date(prefs.privacy_accepted_at).toLocaleString() : "Not recorded"}
            </dd>
            <dt className="text-text-muted">Marketing consent</dt>
            <dd className="text-text-primary flex items-center gap-1.5">
              {prefs.marketing_consent ? (
                <>
                  <ShieldCheck size={14} className="text-bullish" aria-hidden="true" /> Given (separate from Terms
                  acceptance - change anytime in Preferences)
                </>
              ) : (
                "Not given"
              )}
            </dd>
          </dl>
        )}
      </Card>

      <Card>
        <CardHeader
          title="Export your data"
          subtitle="A structured JSON file containing your profile, preferences, watchlists, paper portfolios, experiments, notifications, and support requests. Never includes your password hash or session secrets."
        />
        <a
          href={getAccountExportUrl()}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-md border border-border-strong text-text-secondary text-sm font-medium hover:border-accent hover:text-text-primary w-fit"
        >
          <Download size={16} aria-hidden="true" />
          Export my data
        </a>
        <p className="text-xs text-text-faint mt-3">
          This export exists to make your data portable - it is not, by itself, a claim of GDPR/KVKK compliance.
          See the <a href="/privacy" className="text-accent hover:underline">Privacy Policy</a>.
        </p>
      </Card>

      <Card>
        <CardHeader title="Delete your account" subtitle="Permanently deletes your account and everything it owns." />
        <a href="/settings/account" className="text-sm text-accent hover:underline">
          Go to Account Settings → Delete account
        </a>
      </Card>
    </div>
  );
}
