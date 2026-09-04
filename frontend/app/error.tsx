"use client";

import { useEffect } from "react";
import { AlertTriangle } from "lucide-react";

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    // Client-side only - never sends a raw stack trace to the user's screen.
    console.error(error);
  }, [error]);

  return (
    <div className="mx-auto max-w-md px-4 sm:px-6 py-24 text-center flex flex-col items-center gap-4">
      <AlertTriangle size={32} className="text-warning" aria-hidden="true" />
      <h1 className="text-2xl font-semibold text-text-primary">Something went wrong</h1>
      <p className="text-sm text-text-muted">
        An unexpected error occurred while rendering this page. This has been logged.
      </p>
      <button
        onClick={reset}
        className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-accent text-white text-sm font-medium hover:opacity-90 cursor-pointer"
      >
        Try again
      </button>
    </div>
  );
}
