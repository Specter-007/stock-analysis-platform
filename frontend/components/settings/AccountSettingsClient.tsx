"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, ShieldAlert } from "lucide-react";
import {
  requestEmailVerification, requestEmailChange, changePassword, deleteAccount, ApiError,
} from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Card, CardHeader } from "@/components/ui/Card";

function useActionState() {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  async function run(fn: () => Promise<string>) {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      setMessage(await fn());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }
  return { busy, message, error, run };
}

export function AccountSettingsClient() {
  const { user, logout } = useAuth();
  const router = useRouter();

  const verifyState = useActionState();
  const emailChangeState = useActionState();
  const passwordState = useActionState();

  const [newEmail, setNewEmail] = useState("");
  const [emailChangePassword, setEmailChangePassword] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");

  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  async function handleDelete() {
    setDeleteBusy(true);
    setDeleteError(null);
    try {
      await deleteAccount();
      await logout();
      router.push("/");
    } catch (err) {
      setDeleteError(err instanceof ApiError ? err.message : "Could not delete account.");
    } finally {
      setDeleteBusy(false);
    }
  }

  if (!user) return null;

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader title="Account" />
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
          <dt className="text-text-muted">Email</dt>
          <dd className="text-text-primary">{user.email}</dd>
          <dt className="text-text-muted">Email verified</dt>
          <dd className="text-text-primary">
            {user.email_verified ? "Yes" : (
              <span className="flex items-center gap-2">
                No
                <button
                  onClick={() => verifyState.run(async () => (await requestEmailVerification()).message)}
                  disabled={verifyState.busy}
                  className="text-accent hover:underline text-xs cursor-pointer"
                >
                  Send verification email
                </button>
              </span>
            )}
          </dd>
          <dt className="text-text-muted">Account created</dt>
          <dd className="text-text-primary">{new Date(user.created_at).toLocaleString()}</dd>
        </dl>
        {verifyState.message && <p className="text-xs text-bullish mt-3">{verifyState.message}</p>}
        {verifyState.error && <p className="text-xs text-bearish mt-3">{verifyState.error}</p>}
      </Card>

      <Card>
        <CardHeader title="Change email" subtitle="Requires your current password and confirming the new address." />
        <div className="flex flex-col gap-3">
          <input
            type="email"
            placeholder="New email address"
            value={newEmail}
            onChange={(e) => setNewEmail(e.target.value)}
            className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary"
          />
          <input
            type="password"
            placeholder="Current password"
            value={emailChangePassword}
            onChange={(e) => setEmailChangePassword(e.target.value)}
            className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary"
          />
          <button
            onClick={() =>
              emailChangeState.run(async () => (await requestEmailChange(newEmail, emailChangePassword)).message)
            }
            disabled={emailChangeState.busy || !newEmail || !emailChangePassword}
            className="self-start inline-flex items-center gap-2 px-4 py-2 rounded-md bg-accent text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 cursor-pointer"
          >
            {emailChangeState.busy && <Loader2 size={16} className="animate-spin" aria-hidden="true" />}
            Request email change
          </button>
          {emailChangeState.message && <p className="text-xs text-bullish">{emailChangeState.message}</p>}
          {emailChangeState.error && <p className="text-xs text-bearish">{emailChangeState.error}</p>}
        </div>
      </Card>

      <Card>
        <CardHeader title="Change password" subtitle="You will be signed out of your other sessions." />
        <div className="flex flex-col gap-3">
          <input
            type="password"
            placeholder="Current password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary"
          />
          <input
            type="password"
            placeholder="New password"
            minLength={8}
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary"
          />
          <button
            onClick={() =>
              passwordState.run(async () => (await changePassword(currentPassword, newPassword)).message)
            }
            disabled={passwordState.busy || !currentPassword || !newPassword}
            className="self-start inline-flex items-center gap-2 px-4 py-2 rounded-md bg-accent text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 cursor-pointer"
          >
            {passwordState.busy && <Loader2 size={16} className="animate-spin" aria-hidden="true" />}
            Change password
          </button>
          {passwordState.message && <p className="text-xs text-bullish">{passwordState.message}</p>}
          {passwordState.error && <p className="text-xs text-bearish">{passwordState.error}</p>}
        </div>
      </Card>

      <Card className="border-bearish-dim">
        <CardHeader title="Delete account" subtitle="Permanently deletes your account and all owned data (watchlists, paper portfolios, experiments, notifications). This cannot be undone." />
        {!confirmingDelete ? (
          <button
            onClick={() => setConfirmingDelete(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-md border border-bearish text-bearish text-sm font-medium hover:bg-bearish-dim cursor-pointer"
          >
            <ShieldAlert size={16} aria-hidden="true" />
            Delete my account
          </button>
        ) : (
          <div className="flex flex-col gap-3">
            <p className="text-xs text-bearish">Are you sure? Type nothing needed - click confirm to permanently delete everything.</p>
            {deleteError && <p className="text-xs text-bearish">{deleteError}</p>}
            <div className="flex gap-3">
              <button
                onClick={handleDelete}
                disabled={deleteBusy}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-bearish text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 cursor-pointer"
              >
                {deleteBusy && <Loader2 size={16} className="animate-spin" aria-hidden="true" />}
                Confirm permanent deletion
              </button>
              <button
                onClick={() => setConfirmingDelete(false)}
                className="px-4 py-2 rounded-md border border-border-strong text-text-secondary text-sm cursor-pointer"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
