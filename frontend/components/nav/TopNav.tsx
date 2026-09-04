"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { clsx } from "clsx";
import { ActivitySquare, Menu, Search, X } from "lucide-react";
import { useEffect } from "react";
import { TickerSearch } from "@/components/search/TickerSearch";
import { AccountMenu } from "@/components/auth/AccountMenu";
import { NotificationBell } from "@/components/notifications/NotificationBell";
import { CommandPalette } from "@/components/command-palette/CommandPalette";
import { NavDropdown, type NavDropdownLink } from "@/components/nav/NavDropdown";
import { useDismissableMenu } from "@/hooks/useDismissableMenu";
import { useAuth } from "@/lib/auth-context";

// Full list, used verbatim for the mobile off-canvas panel where there's
// vertical room to show everything without a nested dropdown.
const ALL_LINKS = [
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

// Desktop (>=1280px / `xl`): enough room for four primary links inline plus
// a "Research" dropdown for the rest.
const DESKTOP_PRIMARY_LINKS = [
  { href: "/", label: "Overview" },
  { href: "/analysis", label: "Analysis" },
  { href: "/watchlist", label: "Watchlist" },
  { href: "/paper-trading", label: "Paper Trading" },
];
const DESKTOP_RESEARCH_LINKS: NavDropdownLink[] = [
  { href: "/markets", label: "Markets" },
  { href: "/backtest", label: "Backtesting" },
  { href: "/portfolio", label: "Portfolio" },
  { href: "/compare", label: "Compare" },
  { href: "/experiments", label: "Experiment Lab" },
  { href: "/research", label: "Research History" },
  { href: "/model", label: "Model" },
  { href: "/docs", label: "Docs" },
];

// Tablet (768-1279px / `md` to below `xl`): the header is too narrow for
// four primary links, a search box, and the account controls at once, so
// only the two most-used links stay inline and everything else - including
// Watchlist and Paper Trading - moves into "Menu".
const TABLET_PRIMARY_LINKS = [
  { href: "/", label: "Overview" },
  { href: "/analysis", label: "Analysis" },
];
const TABLET_MENU_LINKS: NavDropdownLink[] = [
  { href: "/watchlist", label: "Watchlist" },
  { href: "/paper-trading", label: "Paper Trading" },
  { href: "/markets", label: "Markets" },
  { href: "/backtest", label: "Backtesting" },
  { href: "/portfolio", label: "Portfolio" },
  { href: "/compare", label: "Compare" },
  { href: "/experiments", label: "Experiment Lab" },
  { href: "/research", label: "Research History" },
  { href: "/model", label: "Model" },
  { href: "/docs", label: "Docs" },
];

function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

function NavLink({ href, label, pathname }: { href: string; label: string; pathname: string }) {
  const active = isActive(pathname, href);
  return (
    <Link
      href={href}
      className={clsx(
        "px-3 py-1.5 rounded text-sm font-medium transition-colors whitespace-nowrap",
        active ? "text-text-primary bg-card-hover" : "text-text-muted hover:text-text-primary hover:bg-card-hover"
      )}
      aria-current={active ? "page" : undefined}
    >
      {label}
    </Link>
  );
}

/** Icon-only search trigger used at narrower widths where an inline search
 * box would no longer fit; opens the same TickerSearch in a small popover. */
function CompactSearchTrigger() {
  const pathname = usePathname();
  const { open, setOpen, close, containerRef, triggerRef } = useDismissableMenu<HTMLDivElement>();

  useEffect(() => {
    close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);

  return (
    <div className="relative" ref={containerRef}>
      <button
        ref={triggerRef}
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="true"
        aria-expanded={open}
        aria-label="Search tickers"
        className="p-2 text-text-muted hover:text-text-primary rounded-md hover:bg-card-hover cursor-pointer"
      >
        <Search size={18} aria-hidden="true" />
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-72 bg-card border border-border rounded-md shadow-lg z-50 p-2">
          <TickerSearch compact autoFocus />
        </div>
      )}
    </div>
  );
}

export default function TopNav() {
  const pathname = usePathname();
  const { user } = useAuth();
  const { open: mobileOpen, setOpen: setMobileOpen, close: closeMobile, containerRef: mobileContainerRef, triggerRef: mobileTriggerRef } =
    useDismissableMenu<HTMLDivElement>();
  useEffect(() => setMobileOpen(false), [pathname, setMobileOpen]);

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-bg/95 backdrop-blur supports-[backdrop-filter]:bg-bg/80">
      <div className="mx-auto max-w-[1600px] px-4 sm:px-6" ref={mobileContainerRef}>
        <div className="flex h-14 items-center justify-between gap-2 md:gap-4">
          <div className="flex items-center gap-4 xl:gap-8 min-w-0">
            <Link href="/" className="flex items-center gap-2 shrink-0 group">
              <ActivitySquare size={20} className="text-accent" aria-hidden="true" />
              <span className="font-semibold text-text-primary tracking-tight text-[15px] hidden sm:inline">
                Stock Analyst
              </span>
            </Link>

            {/* Desktop: >=1280px */}
            <nav className="hidden xl:flex items-center gap-1" aria-label="Primary">
              {DESKTOP_PRIMARY_LINKS.map((link) => (
                <NavLink key={link.href} {...link} pathname={pathname} />
              ))}
              <NavDropdown label="Research" links={DESKTOP_RESEARCH_LINKS} />
            </nav>

            {/* Tablet: 768-1279px */}
            <nav className="hidden md:flex xl:hidden items-center gap-1" aria-label="Primary">
              {TABLET_PRIMARY_LINKS.map((link) => (
                <NavLink key={link.href} {...link} pathname={pathname} />
              ))}
              <NavDropdown label="Menu" links={TABLET_MENU_LINKS} />
            </nav>
          </div>

          <div className="flex items-center gap-1 shrink-0">
            {/* Full search box once there's room for it; icon-only trigger
                on tablet widths where every pixel is already spoken for. */}
            <div className="hidden xl:block mr-1">
              <TickerSearch compact />
            </div>
            <div className="hidden md:block xl:hidden">
              <CompactSearchTrigger />
            </div>

            <button
              onClick={() => document.dispatchEvent(new KeyboardEvent("keydown", { key: "k", ctrlKey: true }))}
              className="hidden xl:flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs text-text-faint border border-border hover:border-border-strong hover:text-text-muted cursor-pointer"
              aria-label="Open command palette"
            >
              <Search size={13} aria-hidden="true" />
              <kbd className="font-mono">Ctrl K</kbd>
            </button>
            <NotificationBell />
            <AccountMenu />

            <button
              ref={mobileTriggerRef}
              className="md:hidden p-2 text-text-muted hover:text-text-primary cursor-pointer"
              onClick={() => setMobileOpen((o) => !o)}
              aria-haspopup="menu"
              aria-label={mobileOpen ? "Close menu" : "Open menu"}
              aria-expanded={mobileOpen}
            >
              {mobileOpen ? <X size={20} aria-hidden="true" /> : <Menu size={20} aria-hidden="true" />}
            </button>
          </div>
        </div>

        {mobileOpen && (
          <div id="mobile-nav-panel" className="md:hidden pb-4 flex flex-col gap-3 border-t border-border pt-3">
            <TickerSearch />
            <nav className="flex flex-col gap-1" aria-label="Primary mobile">
              {ALL_LINKS.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={closeMobile}
                  className={clsx(
                    "px-3 py-2 rounded text-sm font-medium",
                    isActive(pathname, link.href) ? "text-text-primary bg-card-hover" : "text-text-muted hover:text-text-primary"
                  )}
                  aria-current={isActive(pathname, link.href) ? "page" : undefined}
                >
                  {link.label}
                </Link>
              ))}
            </nav>
            {!user && (
              <div className="flex items-center gap-2 border-t border-border pt-3">
                <Link
                  href="/login"
                  onClick={closeMobile}
                  className="flex-1 text-center text-sm text-text-secondary hover:text-text-primary px-3 py-2 rounded-md border border-border"
                >
                  Sign in
                </Link>
                <Link
                  href="/register"
                  onClick={closeMobile}
                  className="flex-1 text-center text-sm bg-accent text-white px-3 py-2 rounded-md font-medium hover:opacity-90"
                >
                  Sign up
                </Link>
              </div>
            )}
          </div>
        )}
      </div>
      <CommandPalette />
    </header>
  );
}
