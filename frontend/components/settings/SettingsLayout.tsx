"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { clsx } from "clsx";
import { RequireAuth } from "@/components/auth/RequireAuth";

const TABS = [
  { href: "/settings/account", label: "Account" },
  { href: "/settings/security", label: "Security" },
  { href: "/settings/preferences", label: "Preferences" },
  { href: "/settings/notifications", label: "Notifications" },
  { href: "/settings/privacy", label: "Privacy" },
];

function SettingsShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    <div className="mx-auto max-w-[900px] px-4 sm:px-6 py-8">
      <h1 className="text-xl font-semibold text-text-primary mb-6">Settings</h1>
      <div className="flex flex-col sm:flex-row gap-6">
        <nav className="flex sm:flex-col gap-1 sm:w-48 shrink-0" aria-label="Settings">
          {TABS.map((tab) => {
            const active = pathname === tab.href;
            return (
              <Link
                key={tab.href}
                href={tab.href}
                className={clsx(
                  "px-3 py-2 rounded-md text-sm font-medium",
                  active ? "bg-card-hover text-text-primary" : "text-text-muted hover:text-text-primary hover:bg-card-hover"
                )}
              >
                {tab.label}
              </Link>
            );
          })}
        </nav>
        <div className="flex-1 min-w-0">{children}</div>
      </div>
    </div>
  );
}

export function SettingsLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireAuth>
      <SettingsShell>{children}</SettingsShell>
    </RequireAuth>
  );
}
