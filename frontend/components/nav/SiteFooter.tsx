import { DISCLAIMER } from "@/lib/constants";

export default function SiteFooter() {
  return (
    <footer className="border-t border-border mt-12">
      <div className="mx-auto max-w-[1600px] px-4 sm:px-6 py-6 flex flex-col gap-2">
        <p className="text-xs text-text-muted leading-relaxed max-w-4xl">
          <span className="font-medium text-text-secondary">Not financial advice.</span> {DISCLAIMER}
        </p>
        <p className="text-xs text-text-faint">
          Market data from Yahoo Finance via the unofficial{" "}
          <code className="font-mono">yfinance</code> library. Data may be delayed, incomplete, or
          temporarily unavailable. Verify important financial information independently.
        </p>
      </div>
    </footer>
  );
}
