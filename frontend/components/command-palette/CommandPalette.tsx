"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  BarChart3, Compass, FileText, FlaskConical, LayoutDashboard, Search, Settings, ShieldQuestion,
  TrendingUp, Wallet,
} from "lucide-react";
import { searchTickers } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { SearchResultItem } from "@/types/api";

interface StaticEntry {
  label: string;
  description: string;
  href: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  category: string;
}

const STATIC_ENTRIES: StaticEntry[] = [
  { label: "Dashboard", description: "Market overview", href: "/", icon: LayoutDashboard, category: "Navigate" },
  { label: "Analysis", description: "Technical analysis for a ticker", href: "/analysis", icon: TrendingUp, category: "Navigate" },
  { label: "Backtesting", description: "Run a historical backtest", href: "/backtest", icon: BarChart3, category: "Navigate" },
  { label: "Portfolio", description: "Multi-ticker portfolio backtest", href: "/portfolio", icon: Wallet, category: "Navigate" },
  { label: "Compare", description: "Compare multiple stocks", href: "/compare", icon: BarChart3, category: "Navigate" },
  { label: "Experiment Lab", description: "Create a reproducible experiment", href: "/experiments", icon: FlaskConical, category: "Research" },
  { label: "Research History", description: "Your past experiments", href: "/research", icon: FlaskConical, category: "Research" },
  { label: "Paper Trading", description: "Your simulated portfolios", href: "/paper-trading", icon: Wallet, category: "Research" },
  { label: "Watchlist", description: "Your tracked tickers", href: "/watchlist", icon: Compass, category: "Research" },
  { label: "Model", description: "Model methodology and scorecard", href: "/model", icon: ShieldQuestion, category: "Research" },
  { label: "Documentation", description: "Methodology and definitions", href: "/docs", icon: FileText, category: "Docs" },
  { label: "Contact / Support", description: "Get in touch", href: "/contact", icon: FileText, category: "Docs" },
  { label: "Account settings", description: "Email, password, sessions", href: "/settings/account", icon: Settings, category: "Settings" },
  { label: "Security settings", description: "Active sessions", href: "/settings/security", icon: Settings, category: "Settings" },
  { label: "Preferences", description: "Timezone, benchmark, theme", href: "/settings/preferences", icon: Settings, category: "Settings" },
];

export function CommandPalette() {
  const router = useRouter();
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [tickerResults, setTickerResults] = useState<SearchResultItem[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const close = useCallback(() => {
    setOpen(false);
    setQuery("");
    setTickerResults([]);
  }, []);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      } else if (e.key === "Escape") {
        close();
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [close]);

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 0);
  }, [open]);

  useEffect(() => {
    const trimmed = query.trim();
    if (trimmed.length < 1) return;
    const controller = new AbortController();
    searchTickers(trimmed, controller.signal)
      .then((res) => !controller.signal.aborted && setTickerResults(res.results.slice(0, 5)))
      .catch(() => !controller.signal.aborted && setTickerResults([]));
    return () => controller.abort();
  }, [query]);

  if (!open) return null;

  const q = query.trim().toLowerCase();
  const visibleTickerResults = q.length === 0 ? [] : tickerResults;
  const filteredStatic = STATIC_ENTRIES.filter(
    (e) =>
      (e.category !== "Research" || user) && // user-owned sections only shown when signed in
      (q.length === 0 || e.label.toLowerCase().includes(q) || e.description.toLowerCase().includes(q))
  );

  function go(href: string) {
    close();
    router.push(href);
  }

  const grouped = filteredStatic.reduce<Record<string, StaticEntry[]>>((acc, entry) => {
    (acc[entry.category] ||= []).push(entry);
    return acc;
  }, {});

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-24 px-4 bg-black/60" onClick={close}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-lg bg-card border border-border-strong rounded-lg shadow-2xl overflow-hidden"
      >
        <div className="flex items-center gap-2 px-4 py-3 border-b border-border">
          <Search size={16} className="text-text-muted shrink-0" aria-hidden="true" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search pages or type a ticker..."
            className="flex-1 bg-transparent text-sm text-text-primary placeholder:text-text-faint outline-none"
          />
          <kbd className="text-[10px] text-text-faint border border-border rounded px-1.5 py-0.5">Esc</kbd>
        </div>

        <div className="max-h-96 overflow-y-auto py-2">
          {visibleTickerResults.length > 0 && (
            <div className="mb-1">
              <p className="px-4 py-1 text-[10px] uppercase tracking-wide text-text-faint">Stocks</p>
              {visibleTickerResults.map((r) => (
                <button
                  key={r.symbol}
                  onClick={() => go(`/analysis?ticker=${encodeURIComponent(r.symbol)}`)}
                  className="w-full flex items-center gap-3 px-4 py-2 text-left hover:bg-card-hover cursor-pointer"
                >
                  <TrendingUp size={14} className="text-accent shrink-0" aria-hidden="true" />
                  <span className="text-sm text-text-primary">{r.symbol}</span>
                  <span className="text-xs text-text-muted truncate">{r.name}</span>
                </button>
              ))}
            </div>
          )}

          {Object.entries(grouped).map(([category, entries]) => (
            <div key={category} className="mb-1">
              <p className="px-4 py-1 text-[10px] uppercase tracking-wide text-text-faint">{category}</p>
              {entries.map((entry) => (
                <button
                  key={entry.href}
                  onClick={() => go(entry.href)}
                  className="w-full flex items-center gap-3 px-4 py-2 text-left hover:bg-card-hover cursor-pointer"
                >
                  <entry.icon size={14} className="text-text-muted shrink-0" />
                  <span className="text-sm text-text-primary">{entry.label}</span>
                  <span className="text-xs text-text-muted truncate">{entry.description}</span>
                </button>
              ))}
            </div>
          ))}

          {visibleTickerResults.length === 0 && Object.keys(grouped).length === 0 && (
            <p className="px-4 py-6 text-sm text-text-muted text-center">No matches.</p>
          )}
        </div>
      </div>
    </div>
  );
}
