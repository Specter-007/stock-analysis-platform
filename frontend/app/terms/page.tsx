import Link from "next/link";
import { LegalPageShell } from "@/components/legal/LegalPageShell";

export const metadata = { title: "Terms of Service — Stock Analyst" };

export default function TermsPage() {
  return (
    <LegalPageShell title="Terms of Service" lastUpdated="2026-09-04">
      <p>By creating an account or using Stock Analyst, you agree to these terms.</p>

      <h2>The service</h2>
      <p>
        Stock Analyst is a research and educational tool that applies a deterministic, rules-based
        quantitative model to market data. It is not a broker, not an investment adviser, and does not execute
        real trades. See the <Link href="/disclaimer" className="text-accent hover:underline">Financial Disclaimer</Link> for
        the full scope of what this application is and is not.
      </p>

      <h2>Your account</h2>
      <ul>
        <li>You must provide accurate information when registering and keep your password confidential.</li>
        <li>You are responsible for all activity that happens under your account.</li>
        <li>You may delete your account at any time from Account Settings; this permanently removes your owned data.</li>
      </ul>

      <h2>Acceptable use</h2>
      <p>You agree not to:</p>
      <ul>
        <li>Attempt to access another user&apos;s account, watchlists, paper portfolios, or experiments.</li>
        <li>Attempt to bypass rate limits, authentication, or other security controls.</li>
        <li>Use the service to send spam, abuse the contact form, or submit unlawful content.</li>
        <li>Reverse-engineer the service in an attempt to extract or resell the underlying market data.</li>
      </ul>

      <h2>No investment advice</h2>
      <p>
        Nothing produced by this application is personalized investment advice. You are solely responsible for
        any decisions you make. See the Financial Disclaimer.
      </p>

      <h2>Service availability</h2>
      <p>
        Market data is sourced from a third party (Yahoo Finance) and may be delayed, incomplete, or
        temporarily unavailable for reasons outside our control. We do not guarantee uninterrupted availability
        of the service or of any particular market data.
      </p>

      <h2>Changes to the service</h2>
      <p>
        We may add, change, or remove features. We do not add billing, brokerage integration, or an AI
        component to the signal-generation logic without updating these terms and the Financial Disclaimer
        accordingly.
      </p>

      <h2>Termination</h2>
      <p>
        We may suspend or terminate an account that violates these terms, in particular the acceptable-use
        section above (e.g. attempting to access another user&apos;s data or abusing rate-limited endpoints).
      </p>

      <h2>Limitation of liability</h2>
      <p>
        The service is provided &quot;as is&quot; without warranties of any kind. To the maximum extent
        permitted by law, we are not liable for any financial loss arising from your use of, or reliance on,
        this application.
      </p>

      <h2>Governing law</h2>
      <p>
        This section intentionally has not been completed with a specific jurisdiction - it should be filled in
        as part of a qualified legal review before this application is used in a production, public-facing
        context.
      </p>
    </LegalPageShell>
  );
}
