"use client";

import { useEffect, useState, useCallback } from "react";
import { Loader2, Monitor, ShieldCheck } from "lucide-react";
import { listSessions, revokeSession, revokeOtherSessions, ApiError } from "@/lib/api";
import type { SessionInfo } from "@/types/auth";
import { Card, CardHeader } from "@/components/ui/Card";

export function SecuritySettingsClient() {
  const [sessions, setSessions] = useState<SessionInfo[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [revokingOthers, setRevokingOthers] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await listSessions();
      setSessions(res.sessions);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load sessions.");
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    listSessions()
      .then((res) => {
        if (!cancelled) setSessions(res.sessions);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Could not load sessions.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleRevoke(id: string) {
    setBusyId(id);
    try {
      await revokeSession(id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not revoke session.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleRevokeOthers() {
    setRevokingOthers(true);
    try {
      await revokeOtherSessions();
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not revoke other sessions.");
    } finally {
      setRevokingOthers(false);
    }
  }

  return (
    <Card>
      <CardHeader
        title="Active sessions"
        subtitle="Every device currently signed into your account."
        action={
          sessions && sessions.length > 1 ? (
            <button
              onClick={handleRevokeOthers}
              disabled={revokingOthers}
              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md border border-border-strong text-text-secondary text-xs font-medium hover:bg-card-hover disabled:opacity-50 cursor-pointer"
            >
              {revokingOthers && <Loader2 size={14} className="animate-spin" aria-hidden="true" />}
              Sign out of all other sessions
            </button>
          ) : undefined
        }
      />
      {error && <p className="text-xs text-bearish mb-3">{error}</p>}
      {!sessions ? (
        <div className="flex items-center gap-2 text-sm text-text-muted">
          <Loader2 size={16} className="animate-spin" aria-hidden="true" /> Loading...
        </div>
      ) : (
        <ul className="flex flex-col divide-y divide-border">
          {sessions.map((s) => (
            <li key={s.id} className="flex items-center justify-between gap-3 py-3">
              <div className="flex items-center gap-3 min-w-0">
                <Monitor size={18} className="text-text-muted shrink-0" aria-hidden="true" />
                <div className="min-w-0">
                  <p className="text-sm text-text-primary truncate flex items-center gap-2">
                    {s.user_agent || "Unknown device"}
                    {s.is_current && (
                      <span className="inline-flex items-center gap-1 text-[10px] uppercase tracking-wide text-bullish bg-bullish-dim px-1.5 py-0.5 rounded">
                        <ShieldCheck size={10} aria-hidden="true" /> This device
                      </span>
                    )}
                  </p>
                  <p className="text-xs text-text-muted">
                    Last active {new Date(s.last_seen_at).toLocaleString()}
                  </p>
                </div>
              </div>
              {!s.is_current && (
                <button
                  onClick={() => handleRevoke(s.id)}
                  disabled={busyId === s.id}
                  className="shrink-0 px-3 py-1.5 rounded-md border border-border-strong text-text-secondary text-xs hover:bg-card-hover disabled:opacity-50 cursor-pointer"
                >
                  Sign out
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
