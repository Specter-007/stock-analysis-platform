"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const STORAGE_KEY = "cookie-consent-ack-v1";

/**
 * This app sets exactly two cookies, both strictly necessary (a session
 * cookie and a CSRF token) - there is no analytics or marketing tracking to
 * consent to. This banner is an acknowledgement of that, not a preference
 * picker with invented categories - see docs/PRIVACY.md.
 */
export function CookieConsentBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    queueMicrotask(() => {
      try {
        if (!localStorage.getItem(STORAGE_KEY)) setVisible(true);
      } catch {
        // Private browsing / storage blocked - don't crash, just skip persistence.
        setVisible(true);
      }
    });
  }, []);

  function acknowledge() {
    try {
      localStorage.setItem(STORAGE_KEY, "1");
    } catch {
      // Ignore - the banner will simply reappear next visit.
    }
    setVisible(false);
  }

  if (!visible) return null;

  return (
    <div className="fixed bottom-0 inset-x-0 z-50 border-t border-border bg-bg-elevated/95 backdrop-blur">
      <div className="mx-auto max-w-[1600px] px-4 sm:px-6 py-3 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <p className="text-xs text-text-muted max-w-2xl">
          This app uses only strictly-necessary cookies (session and CSRF protection) to keep you signed in
          securely. No analytics or advertising cookies are set. See the{" "}
          <Link href="/cookies" className="text-accent hover:underline">
            Cookie Policy
          </Link>{" "}
          for details.
        </p>
        <button
          onClick={acknowledge}
          className="shrink-0 px-3 py-1.5 rounded-md bg-accent text-white text-xs font-medium hover:opacity-90 cursor-pointer"
        >
          Got it
        </button>
      </div>
    </div>
  );
}
