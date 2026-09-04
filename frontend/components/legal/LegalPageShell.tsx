import type { ReactNode } from "react";
import { AlertTriangle } from "lucide-react";

export function LegalPageShell({
  title,
  lastUpdated,
  children,
  showLegalReviewNotice = true,
}: {
  title: string;
  lastUpdated: string;
  children: ReactNode;
  showLegalReviewNotice?: boolean;
}) {
  return (
    <div className="mx-auto max-w-[760px] px-4 sm:px-6 py-10">
      <h1 className="text-2xl font-semibold text-text-primary mb-1">{title}</h1>
      <p className="text-xs text-text-muted mb-6">Last updated: {lastUpdated}</p>

      {showLegalReviewNotice && (
        <div className="flex gap-3 bg-warning-dim border border-warning/30 rounded-md px-4 py-3 mb-8">
          <AlertTriangle size={18} className="text-warning shrink-0 mt-0.5" aria-hidden="true" />
          <p className="text-xs text-text-secondary">
            This document was drafted to accurately describe how this application actually works. It has{" "}
            <strong className="text-text-primary">not been reviewed by a qualified lawyer</strong> and should not
            be treated as a substitute for legal advice or a guarantee of regulatory compliance in any
            jurisdiction. Obtain qualified legal review before relying on this for a production launch.
          </p>
        </div>
      )}

      <div className="prose-legal flex flex-col gap-5 text-sm text-text-secondary leading-relaxed [&_h2]:text-base [&_h2]:font-semibold [&_h2]:text-text-primary [&_h2]:mt-4 [&_ul]:list-disc [&_ul]:pl-5 [&_ul]:flex [&_ul]:flex-col [&_ul]:gap-1.5 [&_strong]:text-text-primary">
        {children}
      </div>
    </div>
  );
}
