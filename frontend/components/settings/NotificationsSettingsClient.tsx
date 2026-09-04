"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { getPreferences, updatePreferences, ApiError } from "@/lib/api";
import type { Preferences } from "@/types/auth";
import { Card, CardHeader } from "@/components/ui/Card";

export function NotificationsSettingsClient() {
  const [prefs, setPrefs] = useState<Preferences | null>(null);
  const [busy, setBusy] = useState(false);
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

  async function save(patch: Partial<Preferences>) {
    setBusy(true);
    setError(null);
    try {
      setPrefs(await updatePreferences(patch));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save.");
    } finally {
      setBusy(false);
    }
  }

  if (!prefs) {
    return (
      <Card>
        <div className="flex items-center gap-2 text-sm text-text-muted">
          <Loader2 size={16} className="animate-spin" aria-hidden="true" /> Loading...
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader
        title="Notification preferences"
        subtitle="These control which real events generate a notification - nothing here is ever simulated."
      />
      <div className="flex flex-col gap-3">
        <label className="flex items-center justify-between gap-3 text-sm text-text-secondary">
          <span>
            <span className="text-text-primary block">In-app notifications for research events</span>
            <span className="text-xs text-text-muted">Experiment completed/failed, paper-trading stop-loss/take-profit triggers</span>
          </span>
          <input
            type="checkbox"
            checked={prefs.research_notifications_enabled}
            onChange={(e) => save({ research_notifications_enabled: e.target.checked })}
          />
        </label>
        <label className="flex items-center justify-between gap-3 text-sm text-text-secondary opacity-60">
          <span>
            <span className="text-text-primary block">Email notifications</span>
            <span className="text-xs text-text-muted">Not yet sent by email in this deployment - stored for when a real email provider is configured</span>
          </span>
          <input
            type="checkbox"
            checked={prefs.email_notifications_enabled}
            onChange={(e) => save({ email_notifications_enabled: e.target.checked })}
          />
        </label>
        {busy && <p className="text-xs text-text-muted">Saving...</p>}
        {error && <p className="text-xs text-bearish">{error}</p>}
      </div>
    </Card>
  );
}
