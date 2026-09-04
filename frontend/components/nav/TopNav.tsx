"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { clsx } from "clsx";
import { ActivitySquare, Menu, Search, X } from "lucide-react";
import { useState } from "react";
import { TickerSearch } from "@/components/search/TickerSearch";
import { AccountMenu } from "@/components/auth/AccountMenu";
import { NotificationBell } from "@/components/notifications/NotificationBell";
import { CommandPalette } from "@/components/command-palette/CommandPalette";

const NAV_LINKS = [
  { href: "/", label: "Overview" },
  { href: "/markets", label: "Markets" },
  { href: "/analysis", label: "Analysis" },
  { href: "/watchlist", label: "Watchlist" },
  { href: "/backtest", label: "Backtesting" },
  { href: "/portfolio", label: "Portfolio" },
  { href: "/compare", label: "Compare" },
  { href: "/experiments", label: "Experiment Lab" },
  { href: "/research", label: "Research History" },
  { href: "/paper-trading", label: "Paper Trading" },
  { href: "/model", label: "Model" },
  { href: "/docs", label: "Docs" },
];

export default function TopNav() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-bg/95 backdrop-blur supports-[backdrop-filter]:bg-bg/80">
      <div className="mx-auto max-w-[1600px] px-4 sm:px-6">
        <div className="flex h-14 items-center justify-between gap-4">
          <div className="flex items-center gap-8 min-w-0">
            <Link href="/" className="flex items-center gap-2 shrink-0 group">
              <ActivitySquare size={20} className="text-accent" aria-hidden="true" />
              <span className="font-semibold text-text-primary tracking-tight text-[15px]">
                Stock Analyst
              </span>
            </Link>
            <nav className="hidden md:flex items-center gap-1" aria-label="Primary">
              {NAV_LINKS.map((link) => {
                const active = link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={clsx(
                      "px-3 py-1.5 rounded text-sm font-medium transition-colors",
                      active
                        ? "text-text-primary bg-card-hover"
                        : "text-text-muted hover:text-text-primary hover:bg-card-hover"
                    )}
                    aria-current={active ? "page" : undefined}
                  >
                    {link.label}
                  </Link>
                );
              })}
            </nav>
          </div>

          <div className="hidden sm:block">
            <TickerSearch compact />
          </div>

          <div className="flex items-center gap-1 shrink-0">
            <button
              onClick={() => document.dispatchEvent(new KeyboardEvent("keydown", { key: "k", ctrlKey: true }))}
              className="hidden lg:flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs text-text-faint border border-border hover:border-border-strong hover:text-text-muted cursor-pointer"
              aria-label="Open command palette"
            >
              <Search size={13} aria-hidden="true" />
              <kbd className="font-mono">Ctrl K</kbd>
            </button>
            <NotificationBell />
            <AccountMenu />
          </div>

          <button
            className="md:hidden p-2 text-text-muted hover:text-text-primary cursor-pointer"
            onClick={() => setMobileOpen((o) => !o)}
            aria-label={mobileOpen ? "Close menu" : "Open menu"}
            aria-expanded={mobileOpen}
          >
            {mobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        {mobileOpen && (
          <div className="md:hidden pb-4 flex flex-col gap-3 border-t border-border pt-3">
            <TickerSearch />
            <nav className="flex flex-col gap-1" aria-label="Primary mobile">
              {NAV_LINKS.map((link) => {
                const active = link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    onClick={() => setMobileOpen(false)}
                    className={clsx(
                      "px-3 py-2 rounded text-sm font-medium",
                      active ? "text-text-primary bg-card-hover" : "text-text-muted hover:text-text-primary"
                    )}
                  >
                    {link.label}
                  </Link>
                );
              })}
            </nav>
          </div>
        )}
      </div>
      <CommandPalette />
    </header>
  );
}
