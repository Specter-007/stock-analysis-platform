import { LegalPageShell } from "@/components/legal/LegalPageShell";

export const metadata = { title: "Cookie Policy — Stock Analyst" };

export default function CookiesPage() {
  return (
    <LegalPageShell title="Cookie Policy" lastUpdated="2026-09-04">
      <p>
        This application sets exactly two cookies. Both are <strong>strictly necessary</strong> - the
        application cannot keep you signed in without them. There are no analytics, advertising, or
        cross-site tracking cookies, and none are invented here to justify a longer policy.
      </p>

      <h2>Cookies we set</h2>
      <ul>
        <li>
          <strong>session_token</strong> - httpOnly (never readable by JavaScript), identifies your signed-in
          session. Without it you would need to sign in again on every request.
        </li>
        <li>
          <strong>csrf_token</strong> - readable by the page&apos;s own JavaScript so it can be echoed back on
          state-changing requests, defending your account against cross-site request forgery.
        </li>
      </ul>

      <h2>What we do not use</h2>
      <ul>
        <li>No Google Analytics, Meta Pixel, or any other analytics/advertising script.</li>
        <li>No third-party embeds that set their own cookies.</li>
        <li>No cookie-based cross-site tracking of any kind.</li>
      </ul>

      <h2>Consent</h2>
      <p>
        Because both cookies are strictly necessary for the application to function, we do not present a
        cookie-preference picker with categories to opt out of - there is nothing non-essential to opt out of.
        The banner shown on your first visit is an acknowledgement, not a consent gate.
      </p>

      <h2>If this changes</h2>
      <p>
        If a future version of this application adds analytics or any non-essential cookie, this policy - and
        the consent banner - will be updated to reflect that honestly before it happens, not after.
      </p>
    </LegalPageShell>
  );
}
