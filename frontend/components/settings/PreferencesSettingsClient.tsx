"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { getPreferences, updatePreferences, ApiError } from "@/lib/api";
import type { Preferences } from "@/types/auth";
import { Card, CardHeader } from "@/components/ui/Card";

const COMMON_TIMEZONES = [
  "UTC", "America/New_York", "America/Chicago", "America/Los_Angeles",
  "Europe/London", "Europe/Berlin", "Europe/Istanbul", "Asia/Tokyo", "Asia/Shanghai", "Australia/Sydney",
];

export function PreferencesSettingsClient() {
  const [prefs, setPrefs] = useState<Preferences | null>(null);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
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
    setSaved(false);
    setError(null);
    try {
      const updated = await updatePreferences(patch);
      setPrefs(updated);
      setSaved(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save preferences.");
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
      <CardHeader title="Research preferences" />
      <div className="flex flex-col gap-4">
        <label className="flex flex-col gap-1.5 text-xs">
          <span className="text-text-muted font-medium">Timezone</span>
          <select
            value={prefs.timezone}
            onChange={(e) => save({ timezone: e.target.value })}
            className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary"
          >
            {[...new Set([prefs.timezone, ...COMMON_TIMEZONES])].map((tz) => (
              <option key={tz} value={tz}>{tz}</option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1.5 text-xs">
          <span className="text-text-muted font-medium">Default benchmark</span>
          <input
            defaultValue={prefs.default_benchmark}
            onBlur={(e) => e.target.value !== prefs.default_benchmark && save({ default_benchmark: e.target.value })}
            className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary max-w-[160px]"
          />
        </label>

        <label className="flex flex-col gap-1.5 text-xs">
          <span className="text-text-muted font-medium">Theme</span>
          <select
            value={prefs.theme}
            onChange={(e) => save({ theme: e.target.value as Preferences["theme"] })}
            className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary max-w-[160px]"
          >
            <option value="dark">Dark</option>
            <option value="light">Light (not yet implemented in the UI)</option>
          </select>
        </label>

        <div className="border-t border-border pt-4 flex flex-col gap-3">
          <label className="flex items-center gap-2 text-sm text-text-secondary">
            <input
              type="checkbox"
              checked={prefs.marketing_consent}
              onChange={(e) => save({ marketing_consent: e.target.checked })}
            />
            Send me occasional product updates
          </label>
        </div>

        {busy && <p className="text-xs text-text-muted">Saving...</p>}
        {saved && !busy && <p className="text-xs text-bullish">Saved.</p>}
        {error && <p className="text-xs text-bearish">{error}</p>}
      </div>
    </Card>
  );
}
