import Link from "next/link";
import { LegalPageShell } from "@/components/legal/LegalPageShell";

export const metadata = { title: "Privacy Policy — Stock Analyst" };

export default function PrivacyPage() {
  return (
    <LegalPageShell title="Privacy Policy" lastUpdated="2026-09-04">
      <p>
        This page describes what data this application actually collects and stores, and why. It intentionally
        does not describe systems that do not exist (there is, for example, no analytics or advertising
        tracking in this application to disclose).
      </p>

      <h2>What we collect</h2>
      <ul>
        <li><strong>Account data:</strong> email address, a securely hashed password (Argon2id - we never store or can see your plaintext password), display name, and account timestamps.</li>
        <li><strong>Session data:</strong> a session identifier and, where legally appropriate, the browser user-agent string and IP address of your active sessions, so you can review and revoke them from Security Settings.</li>
        <li><strong>Preferences:</strong> timezone, default benchmark, theme, and notification settings you choose.</li>
        <li><strong>Your research data:</strong> watchlists, paper-trading portfolios and their simulated trades, and experiments you create - all owned exclusively by your account and never visible to other users.</li>
        <li><strong>Support requests:</strong> the contents of any message you send via the Contact form, associated with your account if you were signed in when you sent it.</li>
      </ul>

      <h2>What we do not collect</h2>
      <ul>
        <li>No analytics, advertising, or third-party tracking cookies.</li>
        <li>No payment or financial account information (this application does not process payments).</li>
        <li>No real brokerage credentials or connections - paper trading is entirely simulated.</li>
      </ul>

      <h2>How we use it</h2>
      <p>
        Solely to operate the application: authenticating you, persisting your research data, showing you your
        own notifications, and responding to support requests. We do not sell or share your data with third
        parties for marketing purposes.
      </p>

      <h2>Server-side access control</h2>
      <p>
        Every piece of your data is scoped to your account at the database level - other users cannot read,
        modify, or delete your watchlists, paper portfolios, experiments, or notifications, and this is
        enforced on the server for every request, not merely hidden in the interface.
      </p>

      <h2>Data retention and deletion</h2>
      <p>
        Deleting your account (Account Settings → Delete account) permanently removes your account and every
        row it owns - preferences, sessions, notifications, watchlists, paper portfolios, and experiments. Past
        support requests you filed are retained for our own operational continuity, with the direct link to
        your account removed.
      </p>

      <h2>Cookies</h2>
      <p>
        We set exactly two cookies, both strictly necessary for the application to function: a session cookie
        (httpOnly - not readable by any script) and a CSRF-protection token. Neither is used for tracking. See
        the <Link href="/cookies" className="text-accent hover:underline">Cookie Policy</Link> for detail.
      </p>

      <h2>Where this may fall short of a specific regulation</h2>
      <p>
        Depending on where you and your users are located, laws such as the EU/UK GDPR or Türkiye&apos;s KVKK
        may impose additional obligations (e.g. a formal legal basis assessment, data processing agreements
        with hosting/email providers, a data protection officer, or specific rights-request handling
        procedures) beyond what is implemented here. This policy describes the current, actual behavior of the
        application - it is not a substitute for a jurisdiction-specific compliance review.
      </p>

      <h2>Contact</h2>
      <p>
        Questions about this policy or your data can be sent via the{" "}
        <Link href="/contact" className="text-accent hover:underline">Contact page</Link>.
      </p>
    </LegalPageShell>
  );
}
