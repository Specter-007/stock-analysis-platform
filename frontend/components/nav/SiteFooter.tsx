import Link from "next/link";
import { DISCLAIMER } from "@/lib/constants";

const LEGAL_LINKS = [
  { href: "/terms", label: "Terms" },
  { href: "/privacy", label: "Privacy" },
  { href: "/cookies", label: "Cookies" },
  { href: "/disclaimer", label: "Disclaimer" },
  { href: "/contact", label: "Contact" },
];

export default function SiteFooter() {
  return (
    <footer className="border-t border-border mt-12">
      <div className="mx-auto max-w-[1600px] px-4 sm:px-6 py-6 flex flex-col gap-3">
        <p className="text-xs text-text-muted leading-relaxed max-w-4xl">
          <span className="font-medium text-text-secondary">Not financial advice.</span> {DISCLAIMER}
        </p>
        <p className="text-xs text-text-faint">
          Market data from Yahoo Finance via the unofficial{" "}
          <code className="font-mono">yfinance</code> library. Data may be delayed, incomplete, or
          temporarily unavailable. Verify important financial information independently.
        </p>
        <nav aria-label="Legal" className="flex flex-wrap gap-x-4 gap-y-1 pt-1">
          {LEGAL_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="text-xs text-text-faint hover:text-text-muted underline-offset-2 hover:underline"
            >
              {link.label}
            </Link>
          ))}
        </nav>
      </div>
    </footer>
  );
}
