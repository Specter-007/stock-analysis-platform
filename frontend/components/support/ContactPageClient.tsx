"use client";

import { useState } from "react";
import { Mail, Loader2 } from "lucide-react";
import { submitContactRequest, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Card } from "@/components/ui/Card";

const CATEGORIES = [
  { value: "ACCOUNT", label: "Account" },
  { value: "BUG_REPORT", label: "Bug report" },
  { value: "DATA_ISSUE", label: "Data issue" },
  { value: "FEATURE_REQUEST", label: "Feature request" },
  { value: "BILLING_QUESTION", label: "Billing question" },
  { value: "OTHER", label: "Other" },
];

export default function ContactPageClient() {
  const { user } = useAuth();
  const [email, setEmail] = useState(user?.email || "");
  const [category, setCategory] = useState("OTHER");
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await submitContactRequest({ contact_email: email, category, subject, message });
      setResult(res.message);
      setSubject("");
      setMessage("");
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        setError("Too many requests. Please wait a moment before trying again.");
      } else {
        setError(err instanceof ApiError ? err.message : "Could not submit your message.");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-lg px-4 sm:px-6 py-12">
      <div className="mb-6 text-center">
        <h1 className="text-xl font-semibold text-text-primary flex items-center justify-center gap-2">
          <Mail size={20} className="text-accent" aria-hidden="true" />
          Contact / Support
        </h1>
        <p className="text-sm text-text-muted mt-1">
          {user ? "Signed in - your message will be linked to your account." : "You don't need an account to reach us."}
        </p>
      </div>

      <Card>
        {result ? (
          <p className="text-sm text-text-secondary">{result}</p>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
            <label className="flex flex-col gap-1.5 text-xs">
              <span className="text-text-muted font-medium">Your email</span>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary"
              />
            </label>

            <label className="flex flex-col gap-1.5 text-xs">
              <span className="text-text-muted font-medium">Category</span>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary"
              >
                {CATEGORIES.map((c) => (
                  <option key={c.value} value={c.value}>{c.label}</option>
                ))}
              </select>
            </label>

            <label className="flex flex-col gap-1.5 text-xs">
              <span className="text-text-muted font-medium">Subject</span>
              <input
                required
                maxLength={200}
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary"
              />
            </label>

            <label className="flex flex-col gap-1.5 text-xs">
              <span className="text-text-muted font-medium">Message</span>
              <textarea
                required
                rows={5}
                maxLength={5000}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary resize-y"
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
              className="self-start inline-flex items-center gap-2 px-4 py-2 rounded-md bg-accent text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 cursor-pointer"
            >
              {busy && <Loader2 size={16} className="animate-spin" aria-hidden="true" />}
              Send message
            </button>
          </form>
        )}
      </Card>
    </div>
  );
}
