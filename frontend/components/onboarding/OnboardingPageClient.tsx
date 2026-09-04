"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Compass, Loader2 } from "lucide-react";
import { updatePreferences, completeOnboarding, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { RequireAuth } from "@/components/auth/RequireAuth";
import { Card, CardHeader } from "@/components/ui/Card";

const COMMON_TIMEZONES = [
  "UTC", "America/New_York", "America/Chicago", "America/Los_Angeles",
  "Europe/London", "Europe/Berlin", "Europe/Istanbul", "Asia/Tokyo", "Asia/Shanghai", "Australia/Sydney",
];

function OnboardingForm() {
  const router = useRouter();
  const { user } = useAuth();
  const [timezone, setTimezone] = useState(
    Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC"
  );
  const [defaultBenchmark, setDefaultBenchmark] = useState("SPY");
  const [researchNotifications, setResearchNotifications] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function finish(skip = false) {
    setBusy(true);
    setError(null);
    try {
      if (!skip) {
        await updatePreferences({
          timezone,
          default_benchmark: defaultBenchmark,
          research_notifications_enabled: researchNotifications,
        });
      }
      await completeOnboarding();
      router.push("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save preferences.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-lg px-4 sm:px-6 py-16">
      <div className="mb-6 text-center">
        <h1 className="text-xl font-semibold text-text-primary flex items-center justify-center gap-2">
          <Compass size={20} className="text-accent" aria-hidden="true" />
          Welcome{user?.display_name ? `, ${user.display_name}` : ""}
        </h1>
        <p className="text-sm text-text-muted mt-1">A couple of quick preferences - skippable, changeable anytime in Settings.</p>
      </div>

      <Card>
        <CardHeader title="Research defaults" />
        <div className="flex flex-col gap-4">
          <label className="flex flex-col gap-1.5 text-xs">
            <span className="text-text-muted font-medium">Timezone</span>
            <select
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary"
            >
              {[...new Set([timezone, ...COMMON_TIMEZONES])].map((tz) => (
                <option key={tz} value={tz}>{tz}</option>
              ))}
            </select>
          </label>

          <label className="flex flex-col gap-1.5 text-xs">
            <span className="text-text-muted font-medium">Default benchmark</span>
            <input
              value={defaultBenchmark}
              onChange={(e) => setDefaultBenchmark(e.target.value.toUpperCase())}
              className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary"
            />
          </label>

          <label className="flex items-center gap-2 text-xs text-text-secondary">
            <input
              type="checkbox"
              checked={researchNotifications}
              onChange={(e) => setResearchNotifications(e.target.checked)}
            />
            Notify me when an experiment finishes or a paper-trading stop triggers
          </label>

          {error && (
            <p role="alert" className="text-xs text-bearish bg-bearish-dim rounded-md px-3 py-2">
              {error}
            </p>
          )}

          <div className="flex items-center justify-between gap-3">
            <button
              onClick={() => finish(true)}
              disabled={busy}
              className="text-xs text-text-muted hover:text-text-primary cursor-pointer"
            >
              Skip for now
            </button>
            <button
              onClick={() => finish(false)}
              disabled={busy}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-accent text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 cursor-pointer"
            >
              {busy && <Loader2 size={16} className="animate-spin" aria-hidden="true" />}
              Finish
            </button>
          </div>
        </div>
      </Card>
    </div>
  );
}

export default function OnboardingPageClient() {
  return (
    <RequireAuth>
      <OnboardingForm />
    </RequireAuth>
  );
}
